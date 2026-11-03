from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Evenement, PaiementFraisEvenement
from .models_notifications_afrofans import (
    PaiementStripeEvenementAfroFans,
)
from .services_notifications_afrofans import (
    notifier_frais_payes,
)


PAYS = {
    "CA": {
        "nom": "Canada",
        "devise": "CAD",
        "moyens": ["Visa", "Mastercard", "Carte bancaire"],
    },
    "ML": {
        "nom": "Mali",
        "devise": "XOF",
        "moyens": ["Orange Money", "Moov Money"],
    },
    "SN": {
        "nom": "Sénégal",
        "devise": "XOF",
        "moyens": ["Wave", "Orange Money", "Free Money"],
    },
    "CI": {
        "nom": "Côte d'Ivoire",
        "devise": "XOF",
        "moyens": [
            "Wave", "Orange Money",
            "MTN Money", "Moov Money",
        ],
    },
}

CENT = Decimal("0.01")


def argent(valeur):
    return Decimal(str(valeur)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def calculer_devis(paiement, pays, province):

    evenement = paiement.evenement

    # Le montant est calculé sur le serveur.
    # 50 FCFA par tranche commencée de 10 billets.
    base_xof = (
        Decimal(evenement.nombre_tranches)
        * Decimal("50")
    )

    resultat = {
        "base_xof": base_xof,
        "pays": pays,
        "province": province,
        "devise": "CAD" if pays == "CA" else "XOF",
        "moyens": PAYS[pays]["moyens"],
        "base": base_xof,
        "tps": Decimal("0"),
        "tvq": Decimal("0"),
        "total": base_xof,
        "taux": None,
        "disponible": False,
        "raison": "",
    }

    # Mali, Sénégal et Côte d'Ivoire :
    # présentation seulement, sans paiement réel.
    if pays in ("ML", "SN", "CI"):
        resultat["raison"] = (
            "Paiement temporairement indisponible "
            "pour ce pays. Contactez le service "
            "clientèle HexaQuébec au 514 467-7377."
        )
        return resultat

    # Cette version ne prend en charge que
    # le traitement fiscal du Québec.
    if province != "QC":
        resultat["raison"] = (
            "Le paiement pour cette province "
            "nécessite une vérification fiscale. "
            "Contactez HexaQuébec au 514 467-7377."
        )
        return resultat

    try:
        taux = Decimal(
            str(
                getattr(
                    settings,
                    "AFROFANS_XOF_TO_CAD",
                    "0",
                )
            )
        )
    except (InvalidOperation, TypeError, ValueError):
        taux = Decimal("0")

    if not taux.is_finite() or taux <= 0:
        resultat["raison"] = (
            "Taux de conversion XOF/CAD non configuré. "
            "Contactez HexaQuébec."
        )
        return resultat

    resultat["taux"] = taux

    base_cad = argent(base_xof * taux)

    # Calcul TPS / TVQ sur le même montant
    # avant taxes.
    tps = argent(base_cad * Decimal("0.05"))
    tvq = argent(base_cad * Decimal("0.09975"))

    resultat["base"] = base_cad
    resultat["tps"] = tps
    resultat["tvq"] = tvq
    resultat["total"] = base_cad + tps + tvq

    # Désactivé tant que le traitement fiscal
    # n'a pas été confirmé.
    if not getattr(
        settings,
        "AFROFANS_TAXES_QC_ACTIVES",
        False,
    ):
        resultat["raison"] = (
            "Le traitement fiscal de ce service "
            "doit être confirmé avant paiement. "
            "Contactez HexaQuébec."
        )
        return resultat

    if resultat["total"] < Decimal("0.50"):
        resultat["raison"] = (
            "Le montant est inférieur au minimum "
            "de paiement par carte. "
            "Contactez HexaQuébec."
        )
        return resultat

    if not getattr(settings, "STRIPE_SECRET_KEY", ""):
        resultat["raison"] = (
            "Le paiement par carte est "
            "temporairement indisponible."
        )
        return resultat

    resultat["disponible"] = True
    return resultat


@login_required
def payer_frais_evenement(request, paiement_id):

    paiement = get_object_or_404(
        PaiementFraisEvenement.objects.select_related(
            "evenement",
            "createur",
        ),
        pk=paiement_id,
        createur=request.user,
    )

    evenement = paiement.evenement

    # Une ancienne demande de paiement ne doit
    # pas être réutilisée après modification.
    dernier_paiement_id = (
        PaiementFraisEvenement.objects
        .filter(evenement=evenement)
        .order_by("-pk")
        .values_list("pk", flat=True)
        .first()
    )

    if dernier_paiement_id != paiement.pk:
        messages.error(
            request,
            "Cette demande de paiement a été remplacée."
        )
        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.pk,
        )

    if (
        paiement.statut == "paye"
        or evenement.frais_billetterie_payes
    ):
        messages.info(
            request,
            "Les frais de cet événement sont déjà payés."
        )
        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.pk,
        )

    pays = (
        request.POST.get("pays")
        if request.method == "POST"
        else request.GET.get("pays")
    )

    province = (
        request.POST.get("province")
        if request.method == "POST"
        else request.GET.get("province")
    )

    pays = pays if pays in PAYS else "CA"

    province = (
        province
        if province in ("QC", "AUTRE")
        else "QC"
    )

    devis = calculer_devis(
        paiement,
        pays,
        province,
    )

    if request.method == "POST":

        if not devis["disponible"]:

            messages.error(
                request,
                devis["raison"] or "Paiement indisponible."
            )

        else:

            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY

                montant_cents = int(
                    (devis["total"] * 100)
                    .to_integral_value()
                )

                retour = request.build_absolute_uri(
                    reverse(
                        "Afrons:detail_evenement",
                        kwargs={
                            "evenement_id": evenement.pk
                        },
                    )
                )

                session = stripe.checkout.Session.create(
                    mode="payment",
                    payment_method_types=["card"],
                    billing_address_collection="required",
                    customer_email=(
                        request.user.email or None
                    ),
                    client_reference_id=str(paiement.pk),
                    line_items=[
                        {
                            "price_data": {
                                "currency": "cad",
                                "unit_amount": montant_cents,
                                "product_data": {
                                    "name": (
                                        "Frais de billetterie "
                                        f"AfroFans · {evenement.titre}"
                                    ),
                                },
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={
                        "paiement_id": str(paiement.pk),
                        "evenement_id": str(evenement.pk),
                    },
                    success_url=(
                        retour + "?paiement=verification"
                    ),
                    cancel_url=(
                        request.build_absolute_uri(
                            request.path
                        )
                        + "?pays=CA&province=QC"
                    ),
                )

                PaiementStripeEvenementAfroFans.objects.create(
                    paiement=paiement,
                    stripe_session_id=session.id,
                    montant_cents=montant_cents,
                    taux_xof_cad=devis["taux"],
                    base_cad=devis["base"],
                    tps_cad=devis["tps"],
                    tvq_cad=devis["tvq"],
                )

                return redirect(session.url)

            except Exception:

                messages.error(
                    request,
                    "Impossible de démarrer le paiement. "
                    "Contactez HexaQuébec au 514 467-7377."
                )

    return render(
        request,
        "Afrons/payer_frais_evenement.html",
        {
            "evenement": evenement,
            "paiement": paiement,
            "pays": pays,
            "province": province,
            "devis": devis,
        },
    )


@csrf_exempt
@require_POST
def webhook_stripe_frais_afrofans(request):

    secret = getattr(
        settings,
        "STRIPE_WEBHOOK_SECRET",
        "",
    )

    if not secret:
        return HttpResponse(status=503)

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        evenement_stripe = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            secret,
        )

    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if evenement_stripe["type"] not in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        return HttpResponse(status=200)

    objet = evenement_stripe["data"]["object"]

    # Une page de succès ne prouve pas le paiement.
    if objet.get("payment_status") != "paid":
        return HttpResponse(status=200)

    session_id = objet.get("id")

    if not session_id:
        return HttpResponse(status=400)

    with transaction.atomic():

        checkout = (
            PaiementStripeEvenementAfroFans.objects
            .select_for_update()
            .select_related("paiement", "paiement__evenement")
            .filter(stripe_session_id=session_id)
            .first()
        )

        if checkout is None:
            return HttpResponse(status=404)

        if checkout.statut == "paye":
            return HttpResponse(status=200)

        if (
            str(objet.get("currency", "")).lower() != "cad"
            or objet.get("amount_total") != checkout.montant_cents
        ):
            return HttpResponse(status=400)

        paiement = checkout.paiement

        evenement = (
            Evenement.objects
            .select_for_update()
            .get(pk=paiement.evenement_id)
        )

        # Une session ancienne ne peut pas
        # débloquer une version modifiée.
        dernier_id = (
            PaiementFraisEvenement.objects
            .filter(evenement=evenement)
            .order_by("-pk")
            .values_list("pk", flat=True)
            .first()
        )

        if dernier_id != paiement.pk:
            checkout.statut = "verification"
            checkout.save(update_fields=["statut"])
            return HttpResponse(status=200)

        # Vérification supplémentaire :
        # le nombre de billets n'a pas changé.
        frais_xof = (
            Decimal(evenement.nombre_tranches)
            * Decimal("50")
        )

        base_attendue = argent(
            frais_xof * checkout.taux_xof_cad
        )

        if base_attendue != checkout.base_cad:
            checkout.statut = "verification"
            checkout.save(update_fields=["statut"])
            return HttpResponse(status=200)

        details = objet.get("customer_details") or {}
        adresse = details.get("address") or {}

        # Si l'adresse réelle ne correspond
        # pas au Québec, examen manuel.
        if (
            adresse.get("country") != "CA"
            or adresse.get("state") not in (
                "QC", "Quebec", "Québec"
            )
        ):
            checkout.statut = "verification"
            checkout.save(update_fields=["statut"])
            return HttpResponse(status=200)

        if paiement.statut != "paye":

            PaiementFraisEvenement.objects.filter(
                pk=paiement.pk
            ).update(
                statut="paye",
                devise_paiement="CAD",
                taux_conversion=checkout.taux_xof_cad,
            )

            Evenement.objects.filter(
                pk=evenement.pk
            ).update(
                frais_billetterie_payes=True,
                frais_payes_le=timezone.now(),
                statut="en_attente",
                notifications_envoyees=False,
            )

        checkout.statut = "paye"
        checkout.paye_le = timezone.now()

        checkout.save(
            update_fields=["statut", "paye_le"]
        )

        evenement_id = evenement.pk

        transaction.on_commit(
            lambda: notifier_frais_payes(
                evenement_id
            )
        )

    return HttpResponse(status=200)