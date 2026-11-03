
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Evenement, BilletEvenement
from .models_billetterie import (
    ReservationExpiration,
    BilletAcces,
)


DUREE_RESERVATION = timedelta(minutes=10)


def capacite_restante(evenement):
    vendues = BilletEvenement.objects.filter(
        evenement=evenement,
        statut="paye",
    ).aggregate(
        total=Sum("quantite")
    )["total"] or 0

    bloquees = ReservationExpiration.objects.filter(
        billet__evenement=evenement,
        billet__statut="en_attente",
        expire_le__gt=timezone.now(),
    ).aggregate(
        total=Sum("billet__quantite")
    )["total"] or 0

    return max(
        evenement.nombre_places - vendues - bloquees,
        0,
    )


@transaction.atomic
def activer_reservation_payee(billet_id):
    """
    À appeler uniquement après vérification réelle
    d'un paiement réussi par le prestataire.

    La vérification du montant, de la devise,
    de la référence et de la signature du
    prestataire doit être faite AVANT cet appel.
    """

    reservation = BilletEvenement.objects.get(
        pk=billet_id
    )

    evenement = Evenement.objects.select_for_update().get(
        pk=reservation.evenement_id
    )

    reservation = (
        BilletEvenement.objects
        .select_for_update()
        .get(pk=billet_id)
    )

    deja_crees = list(
        reservation.billets_individuels.all()
    )

    # Empêche les doubles créations de billets.
    if reservation.statut == "paye":
        if len(deja_crees) == reservation.quantite:
            return deja_crees

        raise ValidationError(
            "Commande payée avec un nombre de "
            "billets incohérent. Vérification requise."
        )

    if reservation.statut != "en_attente":
        raise ValidationError(
            "La réservation ne peut plus être payée."
        )

    if evenement.statut in ("annule", "termine", "refuse"):
        raise ValidationError(
            "L'événement n'accepte plus de paiements."
        )

    blocage = (
        ReservationExpiration.objects
        .select_for_update()
        .filter(billet=reservation)
        .first()
    )

    if not blocage or blocage.expire_le <= timezone.now():
        raise ValidationError(
            "Réservation expirée. Le paiement tardif "
            "doit être traité séparément."
        )

    if deja_crees:
        raise ValidationError(
            "Des QR codes existent déjà pour "
            "cette réservation non payée."
        )

    # La réservation cesse de bloquer des places
    # et devient une vente définitive.
    BilletEvenement.objects.filter(
        pk=reservation.pk,
        statut="en_attente",
    ).update(statut="paye")

    # Chaque place reçoit un billet indépendant.
    billets = []

    for numero in range(reservation.quantite):
        billet_qr = BilletAcces(
            evenement=evenement,
            reservation=reservation,
        )

        billets.append(billet_qr)

    BilletAcces.objects.bulk_create(billets)

    return list(
        BilletAcces.objects.filter(
            reservation=reservation
        ).order_by("cree_le", "pk")
    )
