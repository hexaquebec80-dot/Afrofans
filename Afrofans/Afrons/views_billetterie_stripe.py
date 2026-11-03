
import logging
from decimal import Decimal, ROUND_HALF_UP

import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    BilletEvenement,
    PaiementBilletStripe,
    Evenement,
)

from .services_commission_afrofans import (
    enregistrer_billets_payes,
)

logger = logging.getLogger(__name__)


def euros_ou_dollars_en_centimes(montant):
    valeur = Decimal(str(montant))

    return int(
        (valeur * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


@login_required
@require_POST
def checkout_billet_afrofans(request, code_billet):

    stripe.api_key = settings.STRIPE_SECRET_KEY

    with transaction.atomic():

        reservation = get_object_or_404(
            BilletEvenement.objects
            .select_for_update()
            .select_related("evenement"),
            code_billet=code_billet,
            acheteur=request.user,
        )

        evenement = reservation.evenement

        if reservation.statut != "en_attente":
            return JsonResponse({
                "success": False,
                "erreur": "Réservation non payable.",
            }, status=409)

        if reservation.quantite <= 0:
            return JsonResponse({
                "success": False,
                "erreur": "Quantité invalide.",
            }, status=400)

        # Adapter ce nom si ton modèle utilise
        # un autre champ pour le prix du billet.

        prix_unitaire = evenement.prix_billet

        montant_centimes = (
            euros_ou_dollars_en_centimes(prix_unitaire)
            * reservation.quantite
        )

        devise = getattr(
            settings,
            "AFROFANS_DEVISE_BILLETS",
            "cad",
        ).lower()

        if devise not in ("cad", "eur"):
            return JsonResponse({
                "success": False,
                "erreur": "Devise non autorisée.",
            }, status=400)

        if montant_centimes <= 0:
            return JsonResponse({
                "success": False,
                "erreur": "Montant invalide.",
            }, status=400)

        paiement, cree = (
            PaiementBilletStripe.objects.get_or_create(
                reservation=reservation,
                defaults={
                    "quantite": reservation.quantite,
                    "montant_centimes": montant_centimes,
                    "devise": devise,
                },
            )
        )

        # Ne jamais modifier le montant d'un paiement
        # déjà préparé sans annuler l'ancien Checkout.

        if (
            paiement.montant_centimes != montant_centimes
            or paiement.quantite != reservation.quantite
            or paiement.devise != devise
        ):
            return JsonResponse({
                "success": False,
                "erreur": (
                    "Le montant de la réservation a changé. "
                    "Contactez AfroFans."
                ),
            }, status=409)

        if paiement.statut == "paye":
            return JsonResponse({
                "success": False,
                "erreur": "Billet déjà payé.",
            }, status=409)

        # Réutiliser la session ouverte pour empêcher
        # la création de plusieurs paiements concurrents.

        if paiement.session_stripe:

            session = stripe.checkout.Session.retrieve(
                paiement.session_stripe
            )

            if session.status == "open":
                return JsonResponse({
                    "success": True,
                    "url": session.url,
                })

            return JsonResponse({
                "success": False,
                "erreur": (
                    "Cette session Stripe est terminée. "
                    "La réservation doit être réconciliée "
                    "avant un nouvel essai."
                ),
            }, status=409)

        retour = request.build_absolute_uri(
            reverse(
                "Afrons:confirmation_billet",
                kwargs={
                    "code_billet": reservation.code_billet,
                },
            )
        )

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": devise,
                    "unit_amount": (
                        montant_centimes
                        // reservation.quantite
                    ),
                    "product_data": {
                        "name": (
                            f"Billet AfroFans — "
                            f"{evenement.pk}"
                        ),
                    },
                },
                "quantity": reservation.quantite,
            }],
            success_url=retour + "?paiement=retour",
            cancel_url=retour + "?paiement=annule",
            client_reference_id=str(paiement.pk),
            metadata={
                "type": "billet_afrofans",
                "paiement_id": str(paiement.pk),
                "reservation_id": str(reservation.pk),
                "evenement_id": str(evenement.pk),
            },
            idempotency_key=(
                f"afrofans-billet-checkout-{paiement.pk}"
            ),
        )

        paiement.session_stripe = session.id
        paiement.save(update_fields=["session_stripe"])

    return JsonResponse({
        "success": True,
        "url": session.url,
    })


@csrf_exempt
@require_POST
def webhook_billet_afrofans(request):

    stripe.api_key = settings.STRIPE_SECRET_KEY

    signature = request.headers.get(
        "Stripe-Signature",
        "",
    )

    try:
        evenement_stripe = stripe.Webhook.construct_event(
            request.body,
            signature,
            settings.STRIPE_WEBHOOK_SECRET_BILLETS,
        )

    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if evenement_stripe["type"] not in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        return HttpResponse(status=200)

    session = evenement_stripe["data"]["object"]

    if session.get("payment_status") != "paid":
        return HttpResponse(status=200)

    metadata = session.get("metadata") or {}

    if metadata.get("type") != "billet_afrofans":
        return HttpResponse(status=200)

    try:
        paiement_id = int(metadata["paiement_id"])
    except (KeyError, ValueError, TypeError):
        return HttpResponse(status=400)

    try:
        with transaction.atomic():

            # Verrouiller d'abord l'événement :
            # tous les paiements d'un même événement
            # sont traités dans un ordre cohérent.

            paiement_ref = get_object_or_404(
                PaiementBilletStripe.objects
                .select_related("reservation"),
                pk=paiement_id,
            )

            reservation_ref = paiement_ref.reservation

            evenement = Evenement.objects.select_for_update().get(
                pk=reservation_ref.evenement_id
            )

            paiement = (
                PaiementBilletStripe.objects
                .select_for_update()
                .select_related("reservation")
                .get(pk=paiement_id)
            )

            reservation = paiement.reservation

            if paiement.statut == "paye":
                return HttpResponse(status=200)

            if (
                paiement.session_stripe != session["id"]
                or paiement.montant_centimes
                    != session.get("amount_total")
                or paiement.devise
                    != session.get("currency")
                or metadata.get("reservation_id")
                    != str(reservation.pk)
                or metadata.get("evenement_id")
                    != str(evenement.pk)
            ):
                logger.error(
                    "Incohérence Stripe billet %s",
                    paiement.pk,
                )
                return HttpResponse(status=400)

            if reservation.statut != "en_attente":
                logger.error(
                    "Billet %s dans un état incompatible",
                    reservation.pk,
                )
                return HttpResponse(status=409)

            paiement.statut = "paye"
            paiement.paye_le = timezone.now()
            paiement.payment_intent_stripe = (
                session.get("payment_intent") or ""
            )

            paiement.save(update_fields=[
                "statut",
                "paye_le",
                "payment_intent_stripe",
            ])

            reservation.statut = "paye"
            reservation.save(update_fields=["statut"])

            nouveaux_lots = enregistrer_billets_payes(
                paiement
            )

            logger.info(
                "Paiement %s confirmé. Lots créés : %s",
                paiement.pk,
                [lot.pk for lot in nouveaux_lots],
            )

            # IMPORTANT :
            # Brancher ici ton mécanisme existant de
            # création des BilletAcces et des QR codes.
            # La réservation est maintenant payée,
            # mais ce module ne crée pas les QR codes.

    except Exception:
        logger.exception(
            "Erreur traitement webhook billets AfroFans"
        )
        return HttpResponse(status=500)

    return HttpResponse(status=200)
