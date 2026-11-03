
import io
import secrets

from datetime import timedelta
from hashlib import sha256
from decimal import Decimal

import qrcode
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from django.db import transaction, IntegrityError
from django.db.models import Q

from django.http import (
    HttpResponse,
    HttpResponseForbidden,
)

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.urls import reverse
from django.utils import timezone

from django.views.decorators.cache import never_cache
from django.views.decorators.http import (
    require_POST,
    require_GET,
)

from .models import (
    Evenement,
    BilletEvenement,
    PaiementFraisEvenement,
)

from .models_billetterie import (
    HabilitationBilletterie,
    CodeAccesEvenement,
    ControleurEvenement,
    InvitationControleur,
    ReservationExpiration,
    BilletAcces,
    HistoriqueScan,
)

from .forms_billetterie import (
    EvenementForm,
    AchatBilletForm,
    ControleurEvenementForm,
)

from .services_billetterie import (
    DUREE_RESERVATION,
    capacite_restante,
)


# =====================================================
# 1. AUTORISATIONS
# =====================================================

STATUTS_PUBLICS = ("publie", "ouvert")


def vendeur_verifie(user):
    if not user.is_authenticated:
        return False

    profil = getattr(user, "profil", None)

    if profil is None:
        return False

    if profil.type_compte not in (
        "createur",
        "organisateur",
    ):
        return False

    return HabilitationBilletterie.objects.filter(
        user=user,
        statut="verifie",
    ).exists()



def evenement_du_vendeur(request, evenement_id):
    return get_object_or_404(
        Evenement,
        pk=evenement_id,
        createur=request.user,
    )


# =====================================================
# 2. CRÉER UN ÉVÉNEMENT
# =====================================================

# =====================================================
# AFROFANS - CRÉATION D'ÉVÉNEMENT
#
# DEVISES DES BILLETS :
# - Canada : CAD
# - France : EUR
# - Mali / Sénégal / Côte d'Ivoire : XOF
#
# PAIEMENTS :
# - Canada / France : Stripe
# - Mali / Sénégal / Côte d'Ivoire :
#   moyens locaux temporairement indisponibles
#
# L'événement n'est jamais publié
# avant confirmation des frais et validation.
# =====================================================

@login_required
@transaction.atomic
def creer_evenement(request):

    # ==========================================
    # 1. VÉRIFICATION DU TALENT / ORGANISATEUR
    # ==========================================

    if not vendeur_verifie(request.user):

        messages.error(
            request,
            "Seuls les talents et organisateurs "
            "vérifiés peuvent créer des événements."
        )

        return redirect("Afrons:flux")

    # ==========================================
    # 2. FORMULAIRE SANS AFFICHE
    # ==========================================

    formulaire = EvenementForm(
        request.POST if request.method == "POST" else None
    )

    # ==========================================
    # 3. VALIDATION
    # ==========================================

    if request.method == "POST":

        conditions_acceptees = (
            request.POST.get("accept_conditions") == "oui"
        )

        formulaire_valide = formulaire.is_valid()

        if not conditions_acceptees:

            formulaire.add_error(
                None,
                "Vous devez accepter les conditions "
                "de publication et de billetterie "
                "AfroFans avant de continuer."
            )

        if formulaire_valide and conditions_acceptees:

            # ==================================
            # 4. CRÉATION DE L'ÉVÉNEMENT
            # ==================================

            evenement = formulaire.save(commit=False)

            evenement.createur = request.user

            # Codes de pays du modèle :
            # CA, FR, ML, SN, CI
            evenement.pays = formulaire.cleaned_data[
                "pays"
            ]

            # Devises autorisées par le modèle :
            # CAD, EUR, XOF
            evenement.devise = formulaire.cleaned_data[
                "devise"
            ]

            evenement.statut = "paiement_attente"

            evenement.frais_billetterie_payes = False
            evenement.frais_payes_le = None

            evenement.notifications_envoyees = False

            # ==================================
            # 5. ENREGISTREMENT
            # ==================================

            evenement.save()

            formulaire.save_m2m()

            # ==================================
            # 6. CRÉATION DU DOSSIER DE PAIEMENT
            # ==================================

            # XOF est la devise de référence
            # des frais de billetterie.
            #
            # Le pays du payeur sera sélectionné
            # sur la page de paiement.
            #
            # Aucun paiement n'est confirmé ici.

            paiement = PaiementFraisEvenement.objects.create(
                evenement=evenement,
                createur=request.user,
                devise_paiement="XOF",
                taux_conversion=Decimal("1"),
            )

            # ==================================
            # 7. CONFIRMATION
            # ==================================

            messages.success(
                request,
                "Votre événement a été créé. "
                "Vous devez maintenant régler "
                "les frais de billetterie. "
                "Votre événement sera soumis "
                "à validation après confirmation "
                "du paiement."
            )

            # ==================================
            # 8. PAGE DE PAIEMENT
            # ==================================

            return redirect(
                "Afrons:payer_frais_evenement",
                paiement_id=paiement.pk,
            )

    # ==========================================
    # 9. TAUX DE CONVERSION POUR L'APERÇU
    # ==========================================

    # Ces taux sont définis côté serveur.
    # Il ne faut jamais inventer de taux.
    #
    # Ils servent uniquement à afficher
    # une estimation dans le formulaire.

    taux_xof_cad = getattr(
        settings,
        "AFROFANS_XOF_TO_CAD",
        None,
    )

    taux_xof_eur = getattr(
        settings,
        "AFROFANS_XOF_TO_EUR",
        None,
    )

    # ==========================================
    # 10. AFFICHAGE DU FORMULAIRE
    # ==========================================

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,

            "titre": "Créer un événement",

            "taux_xof_cad": (
                str(taux_xof_cad)
                if taux_xof_cad
                else ""
            ),

            "taux_xof_eur": (
                str(taux_xof_eur)
                if taux_xof_eur
                else ""
            ),

            "telephone_assistance": "514 467-7377",
        },
    )

# =====================================================
# 3. MODIFIER UN ÉVÉNEMENT
# =====================================================

@login_required
@transaction.atomic
def modifier_evenement(request, evenement_id):

    evenement = get_object_or_404(
        Evenement.objects.select_for_update(),
        pk=evenement_id,
        createur=request.user,
    )

    if not vendeur_verifie(request.user):
        return HttpResponseForbidden(
            "Compte non vérifié."
        )

    if evenement.statut in (
        "ouvert",
        "termine",
        "annule",
    ):
        messages.error(
            request,
            "Cet événement ne peut plus être modifié.",
        )

        return redirect(evenement)

    if BilletEvenement.objects.filter(
        evenement=evenement,
        statut="paye",
    ).exists():
        messages.error(
            request,
            "Des billets ont déjà été vendus. "
            "Contacte AfroFans pour modifier "
            "l'événement.",
        )

        return redirect(evenement)

    ancienne_capacite = evenement.nombre_places
    ancien_statut = evenement.statut

    formulaire = EvenementForm(
        request.POST or None,
        request.FILES or None,
        instance=evenement,
    )

    if request.method == "POST" and formulaire.is_valid():

        if request.POST.get("accept_conditions") != "oui":
            formulaire.add_error(
                None,
                "Accepte les conditions pour continuer.",
            )

        else:
            evenement = formulaire.save(commit=False)

            capacite_modifiee = (
                evenement.nombre_places != ancienne_capacite
            )

            if capacite_modifiee:
                evenement.frais_billetterie_payes = False
                evenement.frais_payes_le = None
                evenement.statut = "paiement_attente"

            elif ancien_statut == "paiement_attente":
                evenement.statut = "paiement_attente"

            else:
                evenement.statut = "en_attente"

            evenement.save()
            formulaire.save_m2m()

            if capacite_modifiee:

                paiement = PaiementFraisEvenement.objects.create(
                    evenement=evenement,
                    createur=request.user,
                    devise_paiement="XOF",
                    taux_conversion=Decimal("1"),
                )

                return redirect(
                    "Afrons:payer_frais_evenement",
                    paiement_id=paiement.pk,
                )

            messages.success(
                request,
                "Modifications enregistrées et "
                "envoyées pour validation.",
            )

            return redirect(evenement)

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,
            "titre": "Modifier l'événement",
            "evenement": evenement,
        },
    )


# =====================================================
# 4. DÉTAIL PUBLIC DE L'ÉVÉNEMENT
# =====================================================

# =====================================================
# AFROFANS - DÉTAIL OFFICIEL D'UN ÉVÉNEMENT
# BILLETTERIE - PAIEMENT - PUBLICATION
# =====================================================

def detail_evenement(request, evenement_id):

    # ==========================================
    # 1. ÉVÉNEMENTS ACCESSIBLES AU PUBLIC
    # ==========================================

    # Les fans peuvent consulter uniquement
    # les événements publiés ou ouverts
    # dont les frais de billetterie sont payés.

    filtre = Q(
        pk=evenement_id,
        statut__in=STATUTS_PUBLICS,
        frais_billetterie_payes=True,
    )

    # ==========================================
    # 2. ACCÈS DU TALENT ET DE HEXAQUÉBEC
    # ==========================================

    if request.user.is_authenticated:

        # Le propriétaire peut consulter son
        # événement avant paiement et publication.
        filtre |= Q(
            pk=evenement_id,
            createur=request.user,
        )

        # Les administrateurs peuvent consulter
        # les événements à vérifier.
        if request.user.is_staff:
            filtre |= Q(
                pk=evenement_id,
            )

    # ==========================================
    # 3. RÉCUPÉRER L'ÉVÉNEMENT
    # ==========================================

    evenement = get_object_or_404(
        Evenement.objects.select_related(
            "createur",
            "createur__profil",
        ),
        filtre,
    )

    # ==========================================
    # 4. VÉRIFIER LE PROPRIÉTAIRE
    # ==========================================

    proprietaire = (
        request.user.is_authenticated
        and request.user.pk == evenement.createur_id
    )

    # ==========================================
    # 5. VÉRIFIER LE PAIEMENT DES FRAIS
    # ==========================================

    frais_payes = bool(
        evenement.frais_billetterie_payes
    )

    paiement_en_attente = not frais_payes

    # ==========================================
    # 6. VÉRIFIER LA PUBLICATION
    # ==========================================

    evenement_publie = (
        evenement.statut in STATUTS_PUBLICS
    )

    # La billetterie est ouverte uniquement
    # si les frais sont payés et l'événement
    # officiellement publié ou ouvert.

    billetterie_ouverte = (
        frais_payes
        and evenement_publie
    )

    # ==========================================
    # 7. CALCULER LES PLACES DISPONIBLES
    # ==========================================

    if billetterie_ouverte:

        places_disponibles = max(
            0,
            capacite_restante(evenement)
        )

    else:

        places_disponibles = 0

    # ==========================================
    # 8. AUTORISER LA RÉSERVATION
    # ==========================================

    peut_reserver = (
        billetterie_ouverte
        and places_disponibles > 0
        and not proprietaire
    )

    # ==========================================
    # 9. FORMULAIRE D'ACHAT DES BILLETS
    # ==========================================

    formulaire = AchatBilletForm(
        evenement=evenement,
    )

    # ==========================================
    # 10. INFORMATIONS DU TALENT
    # ==========================================

    talent = evenement.createur

    nom_talent = (
        talent.get_full_name().strip()
        or talent.get_username()
    )

    # ==========================================
    # 11. AFFICHER LA PAGE PROFESSIONNELLE
    # ==========================================

    return render(
        request,
        "Afrons/detail_evenement.html",
        {
            # Événement
            "evenement": evenement,

            # Formulaire de réservation
            "formulaire": formulaire,

            # Talent / organisateur
            "est_proprietaire": proprietaire,
            "talent": talent,
            "nom_talent": nom_talent,

            # Paiement des frais
            "frais_payes": frais_payes,
            "paiement_en_attente": paiement_en_attente,

            # Publication
            "evenement_publie": evenement_publie,
            "billetterie_ouverte": billetterie_ouverte,

            # Billets
            "places_disponibles": places_disponibles,
            "peut_reserver": peut_reserver,

            # Administration HexaQuébec
            "est_administrateur": (
                request.user.is_authenticated
                and request.user.is_staff
            ),
        },
    )


# =====================================================
# 5. ACHETER UN BILLET
# =====================================================

# =====================================================
# AFROFANS - ACHAT ET RÉSERVATION DES BILLETS
# Vérification du talent, du paiement des frais,
# de la disponibilité et du compte Fan.
# =====================================================

@login_required
@require_POST
@transaction.atomic
def acheter_billet(request, evenement_id):

    # ==========================================
    # 1. RÉCUPÉRER L'ÉVÉNEMENT AUTORISÉ
    # ==========================================

    evenement = get_object_or_404(
        Evenement.objects.select_for_update().select_related(
            "createur",
            "createur__profil",
        ),
        pk=evenement_id,
        statut__in=STATUTS_PUBLICS,
        frais_billetterie_payes=True,
    )

    # ==========================================
    # 2. INTERDIRE L'ACHAT AU PROPRIÉTAIRE
    # ==========================================

    if request.user.pk == evenement.createur_id:

        messages.error(
            request,
            "Vous ne pouvez pas acheter "
            "vos propres billets."
        )

        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.pk,
        )

    # ==========================================
    # 3. VÉRIFIER LE COMPTE FAN
    # ==========================================

    profil = getattr(
        request.user,
        "profil",
        None
    )

    if not profil or profil.type_compte != "fan":

        messages.error(
            request,
            "Seuls les utilisateurs possédant "
            "un compte Fan peuvent réserver "
            "des billets sur AfroFans."
        )

        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.pk,
        )

    # ==========================================
    # 4. CONTRÔLER LES PLACES DISPONIBLES
    # ==========================================

    places_disponibles = max(
        0,
        capacite_restante(evenement)
    )

    if places_disponibles <= 0:

        messages.error(
            request,
            "Cet événement est complet. "
            "Aucune place n'est actuellement disponible."
        )

        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.pk,
        )

    # ==========================================
    # 5. INITIALISER LE FORMULAIRE DE RÉSERVATION
    # ==========================================

    formulaire = AchatBilletForm(
        request.POST,
        evenement=evenement,
    )

    # Association du billet
    formulaire.instance.evenement = evenement
    formulaire.instance.acheteur = request.user

    # ==========================================
    # 6. VALIDER LES INFORMATIONS
    # ==========================================

    if formulaire.is_valid():

        billet = formulaire.save(commit=False)

        billet.evenement = evenement
        billet.acheteur = request.user

        # Ce statut ne signifie PAS que le
        # paiement du fan est confirmé.
        billet.statut = "en_attente"

        # ======================================
        # 7. VÉRIFIER LA QUANTITÉ
        # ======================================

        if billet.quantite > places_disponibles:

            formulaire.add_error(
                "quantite",
                (
                    "Il ne reste que "
                    f"{places_disponibles} "
                    "place(s) disponible(s) "
                    "pour cet événement."
                )
            )

        else:

            # ==================================
            # 8. ENREGISTRER LA RÉSERVATION
            # ==================================

            billet.save()

            formulaire.save_m2m()

            # ==================================
            # 9. CRÉER LE DÉLAI D'EXPIRATION
            # ==================================

            expiration = (
                timezone.now()
                + DUREE_RESERVATION
            )

            ReservationExpiration.objects.create(
                billet=billet,
                expire_le=expiration,
            )

            # ==================================
            # 10. CONFIRMATION DE LA RÉSERVATION
            # ==================================

            messages.success(
                request,
                "Votre réservation a été enregistrée. "
                "Finalisez le paiement avant son "
                "expiration pour confirmer votre achat. "
                "Les QR codes de vos billets seront "
                "disponibles uniquement après "
                "confirmation du paiement."
            )

            # ==================================
            # 11. REDIRECTION
            # ==================================

            return redirect(
                "Afrons:confirmation_billet",
                code_billet=billet.code_billet,
            )

    # ==========================================
    # 12. FORMULAIRE INVALIDE
    # RÉAFFICHER LE DESIGN AVEC LES ERREURS
    # ==========================================

    talent = evenement.createur

    nom_talent = (
        talent.get_full_name().strip()
        or talent.get_username()
    )

    return render(
        request,
        "Afrons/detail_evenement.html",
        {
            "evenement": evenement,
            "formulaire": formulaire,

            "est_proprietaire": False,

            "talent": talent,
            "nom_talent": nom_talent,

            "frais_payes": True,
            "paiement_en_attente": False,

            "evenement_publie": True,
            "billetterie_ouverte": True,

            "places_disponibles": places_disponibles,
            "peut_reserver": True,

            "est_administrateur": request.user.is_staff,
        },
        status=400,
    )


# =====================================================
# 6. CONFIRMATION ET MES BILLETS
# =====================================================

# =====================================================
# AFROFANS - CONFIRMATION DES BILLETS
# RÉSERVATION - PAIEMENT - EXPIRATION - QR CODE
# CONTRÔLE TECHNIQUE HEXAQUÉBEC
# =====================================================

@login_required
@never_cache
def confirmation_billet(request, code_billet):

    # ==========================================
    # 1. RÉCUPÉRER LA RÉSERVATION DU FAN
    # ==========================================

    billet = get_object_or_404(
        BilletEvenement.objects.select_related(
            "evenement",
            "acheteur",
        ),
        code_billet=code_billet,
        acheteur=request.user,
    )

    evenement = billet.evenement

    # ==========================================
    # 2. ÉTAT ACTUEL DE LA RÉSERVATION
    # ==========================================

    paiement_confirme = (
        billet.statut == "paye"
    )

    paiement_en_attente = (
        billet.statut == "en_attente"
    )

    billet_annule = (
        billet.statut == "annule"
    )

    # ==========================================
    # 3. VÉRIFIER LE DÉLAI DE RÉSERVATION
    # ==========================================

    blocage = (
        ReservationExpiration.objects
        .filter(billet=billet)
        .order_by("-expire_le")
        .first()
    )

    maintenant = timezone.now()

    reservation_expiree = False
    temps_restant_secondes = 0

    if blocage is not None:

        secondes = (
            blocage.expire_le - maintenant
        ).total_seconds()

        temps_restant_secondes = max(
            0,
            int(secondes)
        )

        # L'expiration concerne une réservation
        # qui n'a pas encore été payée.
        if (
            paiement_en_attente
            and blocage.expire_le <= maintenant
        ):
            reservation_expiree = True

    # ==========================================
    # 4. VÉRIFIER SI LE FAN PEUT ENCORE PAYER
    # ==========================================

    peut_payer = (
        paiement_en_attente
        and not reservation_expiree
        and blocage is not None
        and evenement.statut in ("publie", "ouvert")
        and evenement.frais_billetterie_payes
    )

    # ==========================================
    # 5. RÉCUPÉRER LES BILLETS QR
    # ==========================================

    billets_qr = []

    if paiement_confirme:

        # Les QR codes ne sont affichés que
        # lorsque le paiement a été confirmé
        # par le système de paiement.

        billets_qr = list(
            BilletAcces.objects.filter(
                reservation=billet
            )
            .order_by(
                "cree_le",
                "pk",
            )
        )

    # ==========================================
    # 6. VÉRIFIER LA DISPONIBILITÉ DES QR
    # ==========================================

    qr_disponibles = (
        paiement_confirme
        and len(billets_qr) > 0
    )

    # Nombre de billets effectivement générés
    nombre_qr = len(billets_qr)

    # ==========================================
    # 7. INFORMATIONS DU TALENT
    # ==========================================

    talent = evenement.createur

    nom_talent = (
        talent.get_full_name().strip()
        or talent.get_username()
    )

    # ==========================================
    # 8. MESSAGES D'ÉTAT
    # ==========================================

    if billet_annule:

        statut_message = (
            "Cette réservation a été annulée."
        )

    elif paiement_confirme:

        if qr_disponibles:

            statut_message = (
                "Votre paiement est confirmé. "
                "Vos billets électroniques sont "
                "disponibles avec leurs QR codes."
            )

        else:

            statut_message = (
                "Votre paiement est confirmé, "
                "mais les billets électroniques "
                "ne sont pas encore disponibles. "
                "Contactez le service clientèle "
                "HexaQuébec au 514 467-7377."
            )

    elif reservation_expiree:

        statut_message = (
            "Votre délai de réservation a expiré. "
            "Vous devez effectuer une nouvelle "
            "réservation si des places sont "
            "encore disponibles."
        )

    elif peut_payer:

        statut_message = (
            "Votre réservation est enregistrée. "
            "Finalisez votre paiement avant "
            "l'expiration du délai pour "
            "recevoir vos QR codes."
        )

    else:

        statut_message = (
            "Votre réservation est en attente. "
            "Le paiement n'est pas disponible "
            "pour le moment. Contactez le "
            "service clientèle HexaQuébec "
            "au 514 467-7377 si nécessaire."
        )

    # ==========================================
    # 9. AFFICHER LA PAGE DE CONFIRMATION
    # ==========================================

    return render(
        request,
        "Afrons/confirmation_billet.html",
        {
            # Réservation
            "billet": billet,
            "evenement": evenement,

            # Talent
            "talent": talent,
            "nom_talent": nom_talent,

            # État du paiement
            "paiement_confirme": paiement_confirme,
            "paiement_en_attente": paiement_en_attente,
            "billet_annule": billet_annule,
            "peut_payer": peut_payer,

            # Expiration
            "blocage": blocage,
            "reservation_expiree": reservation_expiree,
            "temps_restant_secondes": (
                temps_restant_secondes
            ),

            # Billets électroniques
            "billets_qr": billets_qr,
            "qr_disponibles": qr_disponibles,
            "nombre_qr": nombre_qr,

            # Message
            "statut_message": statut_message,

            # Assistance HexaQuébec
            "telephone_assistance": "514 467-7377",
        },
    )



# =====================================================
# 7. OUVRIR UN ÉVÉNEMENT
# =====================================================

# =====================================================
# AFROFANS - OUVERTURE OFFICIELLE D'UN ÉVÉNEMENT
# PAIEMENT - VALIDATION - CONTRÔLEURS - SÉCURITÉ
# CONTRÔLE TECHNIQUE HEXAQUÉBEC
# =====================================================

@login_required
@require_POST
@transaction.atomic
def ouvrir_evenement(request, evenement_id):

    # ==========================================
    # 1. VÉRIFIER LE TALENT / ORGANISATEUR
    # ==========================================

    if not vendeur_verifie(request.user):

        messages.error(
            request,
            "Votre compte Talent ou Organisateur "
            "doit être vérifié pour ouvrir "
            "un événement AfroFans."
        )

        return redirect("Afrons:flux")

    # ==========================================
    # 2. RÉCUPÉRER L'ÉVÉNEMENT DU PROPRIÉTAIRE
    # ==========================================

    evenement = get_object_or_404(
        Evenement.objects.select_for_update(),
        pk=evenement_id,
        createur=request.user,
    )

    destination = "Afrons:tableau_presence"

    # ==========================================
    # 3. VÉRIFIER LE PAIEMENT DES FRAIS
    # ==========================================

    if not evenement.frais_billetterie_payes:

        messages.error(
            request,
            "Impossible d'ouvrir cet événement. "
            "Les frais de billetterie ne sont "
            "pas encore confirmés. "
            "Veuillez effectuer votre paiement."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    # Vérifier également le dernier paiement
    # enregistré dans la base de données.

    dernier_paiement = (
        PaiementFraisEvenement.objects
        .filter(evenement=evenement)
        .order_by("-pk")
        .first()
    )

    if (
        dernier_paiement is None
        or dernier_paiement.statut != "paye"
    ):

        messages.error(
            request,
            "Le paiement de cet événement "
            "n'a pas été confirmé par le "
            "système de paiement AfroFans. "
            "Contactez HexaQuébec au "
            "514 467-7377 si nécessaire."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    # ==========================================
    # 4. VÉRIFIER LA PUBLICATION
    # ==========================================

    if evenement.statut == "ouvert":

        messages.info(
            request,
            "Cet événement est déjà ouvert."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    if evenement.statut == "termine":

        messages.error(
            request,
            "Cet événement est terminé "
            "et ne peut plus être ouvert."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    if evenement.statut == "annule":

        messages.error(
            request,
            "Cet événement a été annulé "
            "et ne peut plus être ouvert."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    if evenement.statut != "publie":

        messages.error(
            request,
            "Votre événement doit d'abord "
            "être validé et publié officiellement "
            "par AfroFans avant son ouverture."
        )

        return redirect(
            destination,
            evenement_id=evenement.pk,
        )

    # ==========================================
    # 5. GÉNÉRER LE CODE UNIQUE
    # ==========================================

    # Si un code existe déjà pour cet événement,
    # on conserve le même.
    # Sinon, le modèle CodeAccesEvenement
    # doit générer son code lors de la création.

    code_acces, code_cree = (
        CodeAccesEvenement.objects.get_or_create(
            evenement=evenement
        )
    )

    # ==========================================
    # 6. OUVRIR OFFICIELLEMENT L'ÉVÉNEMENT
    # ==========================================

    evenement.statut = "ouvert"

    evenement.save(
        update_fields=["statut"]
    )

    # ==========================================
    # 7. MESSAGE DE CONFIRMATION
    # ==========================================

    if code_cree:

        messages.success(
            request,
            "Votre événement est maintenant ouvert "
            "sur AfroFans. Un code d'accès unique "
            "a été créé pour vos contrôleurs. "
            "Communiquez-le uniquement aux "
            "contrôleurs autorisés."
        )

    else:

        messages.success(
            request,
            "Votre événement est maintenant ouvert "
            "sur AfroFans. Votre code d'accès "
            "existant reste valide pour "
            "les contrôleurs autorisés."
        )

    # ==========================================
    # 8. REDIRECTION VERS LE TABLEAU DE GESTION
    # ==========================================

    return redirect(
        destination,
        evenement_id=evenement.pk,
    )


# =====================================================
# 8. TERMINER UN ÉVÉNEMENT
# =====================================================

@login_required
@require_POST
@transaction.atomic
def terminer_evenement(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    evenement = (
        Evenement.objects
        .select_for_update()
        .get(pk=evenement.pk)
    )

    if evenement.statut == "ouvert":

        evenement.statut = "termine"
        evenement.save(update_fields=["statut"])

        messages.success(
            request,
            "Événement terminé. Les billets "
            "non utilisés sont désormais "
            "classés comme absents.",
        )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=evenement.pk,
    )

# =====================================================
# AFROFANS - INVITATION CONTRÔLEUR PROFESSIONNELLE
# DESIGN HTML - CONTRÔLE TECHNIQUE HEXAQUÉBEC
# =====================================================

def envoyer_invitation_controleur(request, controleur):

    # 1. Générer le jeton personnel sécurisé
    jeton = secrets.token_urlsafe(32)

    empreinte = sha256(
        jeton.encode("utf-8")
    ).hexdigest()

    # 2. Enregistrer l'invitation valable 48 heures
    invitation, _ = InvitationControleur.objects.update_or_create(
        controleur=controleur,
        defaults={
            "empreinte_jeton": empreinte,
            "expire_le": timezone.now() + timedelta(hours=48),
            "utilise_le": None,
        },
    )

    # 3. Construire le lien personnel d'accès
    lien = request.build_absolute_uri(
        reverse(
            "Afrons:invitation_controleur",
            args=[controleur.pk, jeton],
        )
    )

    # 4. Préparer les données du design HTML
    contexte = {
        "prenom": controleur.prenom,
        "nom": controleur.nom,
        "titre_evenement": controleur.evenement.titre,
        "lien": lien,
        "annee": timezone.localdate().year,
    }

    # 5. Générer le courriel HTML professionnel
    contenu_html = render_to_string(
        "Afrons/emails/invitation_controleur.html",
        contexte,
    )

    # 6. Version texte pour les clients email
    # qui ne prennent pas en charge le HTML
    contenu_texte = (
        f"Bonjour {controleur.prenom} {controleur.nom},\n\n"
        "Vous êtes invité à devenir contrôleur "
        "de billets pour un événement AfroFans.\n\n"
        f"Événement : {controleur.evenement.titre}\n\n"
        f"Votre lien personnel :\n{lien}\n\n"
        "Cette invitation expire dans 48 heures.\n\n"
        "Le talent ou l'organisateur vous communiquera "
        "séparément le code unique de l'événement.\n\n"
        "Ne partagez pas cette invitation.\n\n"
        "AfroFans\n"
        "Billetterie et contrôle d'accès développés "
        "et contrôlés techniquement par HexaQuébec."
    )

    # 7. Préparer le courriel
    email = EmailMultiAlternatives(
        subject=(
            "AfroFans | Invitation officielle "
            "à contrôler un événement"
        ),
        body=contenu_texte,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[controleur.email],
    )

    # 8. Joindre la version HTML
    email.attach_alternative(
        contenu_html,
        "text/html",
    )

    # 9. Envoyer le message
    email.send(fail_silently=False)

    return invitation

# =====================================================
# 10. CRÉER UN CONTRÔLEUR
# =====================================================

@login_required
def creer_controleur(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    if not vendeur_verifie(request.user):
        return HttpResponseForbidden(
            "Compte vendeur non vérifié."
        )

    if evenement.statut not in ("publie", "ouvert"):
        return HttpResponseForbidden(
            "L'événement n'est pas encore "
            "autorisé à recevoir des contrôleurs."
        )

    formulaire = ControleurEvenementForm(
        request.POST or None
    )

    if request.method == "POST" and formulaire.is_valid():

        controleur = formulaire.save(commit=False)
        controleur.evenement = evenement

        if ControleurEvenement.objects.filter(
            evenement=evenement,
            email=controleur.email,
        ).exists():
            formulaire.add_error(
                "email",
                "Ce contrôleur existe déjà "
                "pour cet événement.",
            )

        else:
            try:
                controleur.save()

            except IntegrityError:
                formulaire.add_error(
                    "email",
                    "Adresse déjà utilisée.",
                )

            else:
                try:
                    envoyer_invitation_controleur(
                        request,
                        controleur,
                    )

                except Exception:
                    messages.warning(
                        request,
                        "Contrôleur enregistré, mais "
                        "le courriel n'a pas été envoyé. "
                        "Vérifie le SMTP et renvoie "
                        "l'invitation.",
                    )

                else:
                    messages.success(
                        request,
                        "Contrôleur créé. Invitation "
                        "envoyée à son courriel.",
                    )

                return redirect(
                    "Afrons:tableau_presence",
                    evenement_id=evenement.pk,
                )

    return render(
        request,
        "Afrons/formulaire_controleur.html",
        {
            "evenement": evenement,
            "formulaire": formulaire,
        },
    )


# =====================================================
# 11. RENVOYER UNE INVITATION
# =====================================================

@login_required
@require_POST
def renvoyer_invitation(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        evenement__createur=request.user,
    )

    if not controleur.actif:
        return HttpResponseForbidden(
            "Contrôleur désactivé."
        )

    try:
        envoyer_invitation_controleur(
            request,
            controleur,
        )

    except Exception:
        messages.error(
            request,
            "Impossible d'envoyer le courriel.",
        )

    else:
        messages.success(
            request,
            "Nouvelle invitation envoyée.",
        )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=controleur.evenement_id,
    )


# =====================================================
# 12. DÉSACTIVER UN CONTRÔLEUR
# =====================================================

@login_required
@require_POST
def desactiver_controleur(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement,
        pk=controleur_id,
        evenement__createur=request.user,
    )

    controleur.actif = False
    controleur.save(update_fields=["actif"])

    messages.success(
        request,
        "Accès du contrôleur désactivé.",
    )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=controleur.evenement_id,
    )


# =====================================================
# 13. SESSION PRIVÉE DU CONTRÔLEUR
# =====================================================

def controleur_connecte(request, controleur):

    session = request.session.get(
        f"af_controle_{controleur.pk}",
        {},
    )

    return bool(
        controleur.actif
        and controleur.evenement.statut == "ouvert"
        and session.get("ok")
        and session.get("expire", 0)
        > timezone.now().timestamp()
    )


# =====================================================
# 14. LE CONTRÔLEUR CLIQUE SUR SON LIEN
# =====================================================

@never_cache
def invitation_controleur(
    request,
    controleur_id,
    jeton,
):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        actif=True,
    )

    invitation = get_object_or_404(
        InvitationControleur,
        controleur=controleur,
    )

    if not invitation.jeton_est_valide(jeton):
        return HttpResponseForbidden(
            "Invitation invalide, déjà utilisée "
            "ou expirée. Demande un nouveau lien."
        )

    request.session.cycle_key()

    request.session[
        f"af_invite_{controleur.pk}"
    ] = {
        "empreinte": invitation.empreinte_jeton,
        "expire": invitation.expire_le.timestamp(),
    }

    return redirect(
        "Afrons:code_controleur",
        controleur_id=controleur.pk,
    )


# =====================================================
# 15. SAISIE DU CODE UNIQUE DE L'ÉVÉNEMENT
# =====================================================

@never_cache
def code_controleur(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        actif=True,
    )

    if controleur.evenement.statut != "ouvert":
        return HttpResponseForbidden(
            "Cet événement n'est pas encore ouvert."
        )

    if controleur_connecte(request, controleur):
        return redirect(
            "Afrons:scanner_evenement",
            controleur_id=controleur.pk,
        )

    donnees = request.session.get(
        f"af_invite_{controleur.pk}"
    )

    invitation = InvitationControleur.objects.filter(
        controleur=controleur
    ).first()

    valide = (
        isinstance(donnees, dict)
        and invitation is not None
        and invitation.utilise_le is None
        and invitation.expire_le > timezone.now()
        and donnees.get("expire", 0)
        > timezone.now().timestamp()
        and secrets.compare_digest(
            donnees.get("empreinte", ""),
            invitation.empreinte_jeton,
        )
    )

    if not valide:
        return HttpResponseForbidden(
            "Accès refusé. Utilise le lien "
            "d'invitation reçu par courriel."
        )

    if request.method == "POST":

        maintenant = timezone.now().timestamp()

        cle_essais = f"af_essais_{controleur.pk}"

        essais = request.session.get(
            cle_essais,
            [],
        )

        essais = [
            instant
            for instant in essais
            if maintenant - instant < 900
        ]

        if len(essais) >= 5:
            return HttpResponseForbidden(
                "Trop de tentatives. Réessaie "
                "dans 15 minutes."
            )

        essais.append(maintenant)
        request.session[cle_essais] = essais

        code_saisi = (
            request.POST.get(
                "code_evenement",
                "",
            ).strip().upper()
        )

        code_acces = CodeAccesEvenement.objects.filter(
            evenement=controleur.evenement
        ).first()

        code_valide = (
            code_acces is not None
            and secrets.compare_digest(
                code_saisi,
                code_acces.code,
            )
        )

        if code_valide:

            with transaction.atomic():
                modifie = InvitationControleur.objects.filter(
                    pk=invitation.pk,
                    empreinte_jeton=invitation.empreinte_jeton,
                    utilise_le__isnull=True,
                    expire_le__gt=timezone.now(),
                ).update(
                    utilise_le=timezone.now()
                )

            if modifie != 1:
                return HttpResponseForbidden(
                    "Invitation déjà utilisée ou expirée."
                )

            request.session[
                f"af_controle_{controleur.pk}"
            ] = {
                "ok": True,
                "expire": maintenant + 8 * 3600,
            }

            request.session.pop(
                f"af_invite_{controleur.pk}",
                None,
            )

            request.session.pop(
                cle_essais,
                None,
            )

            return redirect(
                "Afrons:scanner_evenement",
                controleur_id=controleur.pk,
            )

        messages.error(
            request,
            "Code événement incorrect.",
        )

    return render(
        request,
        "Afrons/code_controleur.html",
        {
            "controleur": controleur,
        },
    )


# =====================================================
# 16. SCANNER LES BILLETS QR
# =====================================================

@never_cache
def scanner_evenement(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
    )

    if not controleur_connecte(request, controleur):
        return HttpResponseForbidden(
            "Session expirée ou accès révoqué."
        )

    resultat = None
    billet = None

    if request.method == "POST":

        jeton = request.POST.get(
            "ticket_token",
            "",
        ).strip()

        if not jeton or len(jeton) > 1000:
            resultat = "QR code invalide."

        else:
            try:
                contenu = signing.loads(
                    jeton,
                    salt="afrofans-ticket-v1",
                )

                billet_id = contenu["ticket_id"]
                evenement_qr = contenu["event_id"]

                if (
                    evenement_qr
                    != controleur.evenement_id
                ):
                    resultat = (
                        "Billet d'un autre événement."
                    )

                else:
                    with transaction.atomic():

                        billet = (
                            BilletAcces.objects
                            .select_for_update()
                            .select_related("reservation")
                            .filter(pk=billet_id)
                            .first()
                        )

                        if billet is None:
                            resultat = (
                                "Billet inexistant."
                            )

                        else:
                            if (
                                billet.evenement_id
                                != controleur.evenement_id
                            ):
                                resultat = (
                                    "Billet d'un autre événement."
                                )
                                code_resultat = "autre_evenement"

                            elif (
                                billet.reservation.statut
                                != "paye"
                                or billet.statut == "annule"
                            ):
                                resultat = (
                                    "Billet non valide ou annulé."
                                )
                                code_resultat = "annule"

                            elif billet.statut == "utilise":
                                resultat = (
                                    "Billet déjà utilisé."
                                )
                                code_resultat = "deja_utilise"

                            elif (
                                not billet.prenom_participant
                                or not billet.nom_participant
                            ):
                                resultat = (
                                    "Identité du participant "
                                    "non renseignée."
                                )
                                code_resultat = "incomplet"

                            else:
                                instant = timezone.now()

                                modifie = (
                                    BilletAcces.objects
                                    .filter(
                                        pk=billet.pk,
                                        statut="actif",
                                    )
                                    .update(
                                        statut="utilise",
                                        utilise_le=instant,
                                        controleur_entree=controleur,
                                    )
                                )

                                if modifie:
                                    billet.statut = "utilise"
                                    billet.utilise_le = instant
                                    resultat = "ENTRÉE VALIDÉE"
                                    code_resultat = "valide"

                                else:
                                    resultat = (
                                        "Billet déjà utilisé."
                                    )
                                    code_resultat = "deja_utilise"

                            HistoriqueScan.objects.create(
                                billet=billet,
                                controleur=controleur,
                                resultat=code_resultat,
                            )

            except (
                signing.BadSignature,
                ValueError,
                KeyError,
                TypeError,
                ValidationError,
            ):
                resultat = "QR code inconnu ou falsifié."

    return render(
        request,
        "Afrons/scanner_evenement.html",
        {
            "controleur": controleur,
            "resultat": resultat,
            "billet_scanne": billet,
        },
    )


# =====================================================
# 17. TABLEAU DE PRÉSENCE DU TALENT
# =====================================================

@login_required
@never_cache
def tableau_presence(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    billets = list(
        BilletAcces.objects.filter(
            evenement=evenement,
            reservation__statut="paye",
        ).select_related(
            "reservation__acheteur",
            "controleur_entree",
        ).order_by(
            "nom_participant",
            "prenom_participant",
        )
    )

    presents = sum(
        billet.statut == "utilise"
        for billet in billets
    )

    non_entres = [
        billet
        for billet in billets
        if billet.statut == "actif"
    ]

    controleurs = ControleurEvenement.objects.filter(
        evenement=evenement
    )

    code_acces = CodeAccesEvenement.objects.filter(
        evenement=evenement
    ).first()

    return render(
        request,
        "Afrons/tableau_presence.html",
        {
            "evenement": evenement,
            "billets": billets,
            "presents": presents,
            "non_entres": non_entres,
            "nombre_total": len(billets),
            "controleurs": controleurs,
            "code_acces": code_acces,
            "cloture": evenement.statut == "termine",
        },
    )


# =====================================================
# 18. CRÉER L'IMAGE QR DU BILLET
# =====================================================

@login_required
@require_GET
@never_cache
def image_qr_billet(request, billet_id):

    billet = get_object_or_404(
        BilletAcces.objects.select_related(
            "reservation",
        ),
        pk=billet_id,
        reservation__acheteur=request.user,
        reservation__statut="paye",
    )

    if billet.statut == "annule":
        return HttpResponseForbidden(
            "Billet annulé."
        )

    if (
        not billet.prenom_participant
        or not billet.nom_participant
    ):
        return HttpResponseForbidden(
            "Renseigne le nom et le prénom "
            "du participant."
        )

    image = qrcode.make(
        billet.jeton_qr()
    )

    tampon = io.BytesIO()
    image.save(tampon, format="PNG")

    reponse = HttpResponse(
        tampon.getvalue(),
        content_type="image/png",
    )

    reponse["Cache-Control"] = (
        "no-store, private"
    )

    return reponse


# =====================================================
# 19. NOMMER CHAQUE PARTICIPANT
# =====================================================

@login_required
@require_POST
@transaction.atomic
def nommer_participant(request, billet_id):

    billet = get_object_or_404(
        BilletAcces.objects
        .select_for_update()
        .select_related(
            "reservation",
            "evenement",
        ),
        pk=billet_id,
        reservation__acheteur=request.user,
        reservation__statut="paye",
        statut="actif",
    )

    if billet.evenement.statut in (
        "termine",
        "annule",
    ):
        return HttpResponseForbidden(
            "Événement terminé ou annulé."
        )

    prenom = request.POST.get(
        "prenom", ""
    ).strip()

    nom = request.POST.get(
        "nom", ""
    ).strip()

    if (
        not prenom
        or not nom
        or len(prenom) > 100
        or len(nom) > 100
    ):
        messages.error(
            request,
            "Indique le nom et le prénom "
            "(100 caractères maximum).",
        )

    else:
        billet.prenom_participant = prenom
        billet.nom_participant = nom

        billet.save(
            update_fields=[
                "prenom_participant",
                "nom_participant",
            ]
        )

        messages.success(
            request,
            "Participant enregistré.",
        )

    return redirect(
        "Afrons:confirmation_billet",
        code_billet=billet.reservation.code_billet,
    )
