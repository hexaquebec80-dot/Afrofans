
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .models import (
    BilletUnitePayeeAfroFans,
    LotCommissionAfroFans,
)


TAILLE_LOT = 20
TAUX_COMMISSION = Decimal("0.05")


def calculer_commission_centimes(montant_centimes):
    return int(
        (
            Decimal(montant_centimes)
            * TAUX_COMMISSION
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def enregistrer_billets_payes(paiement):
    """
    Appeler uniquement après confirmation réelle
    du paiement Stripe.

    Le verrouillage de l'événement doit être pris
    par la transaction appelante avant cette fonction.
    """

    reservation = paiement.reservation
    evenement = reservation.evenement

    if paiement.statut != "paye":
        raise ValueError("Paiement non confirmé.")

    quantite = paiement.quantite

    if quantite <= 0:
        raise ValueError("Quantité invalide.")

    # Répartir les éventuels centimes restants
    # sans perdre de montant.

    prix_base, reste = divmod(
        paiement.montant_centimes,
        quantite,
    )

    for index in range(quantite):

        montant_unite = (
            prix_base + (1 if index < reste else 0)
        )

        BilletUnitePayeeAfroFans.objects.get_or_create(
            paiement=paiement,
            numero_unite=index + 1,
            defaults={
                "evenement": evenement,
                "montant_centimes": montant_unite,
                "devise": paiement.devise,
            },
        )

    nouveaux_lots = []

    while True:

        disponibles = list(
            BilletUnitePayeeAfroFans.objects
            .filter(
                evenement=evenement,
                lot__isnull=True,
            )
            .order_by("pk")[:TAILLE_LOT]
        )

        if len(disponibles) < TAILLE_LOT:
            break

        devises = {item.devise for item in disponibles}

        if len(devises) != 1:
            raise ValueError(
                "Un lot ne peut pas mélanger "
                "plusieurs devises."
            )

        montant_brut = sum(
            item.montant_centimes
            for item in disponibles
        )

        commission = calculer_commission_centimes(
            montant_brut
        )

        nombre_lots = (
            LotCommissionAfroFans.objects
            .filter(evenement=evenement)
            .count()
        )

        lot = LotCommissionAfroFans.objects.create(
            evenement=evenement,
            numero_lot=nombre_lots + 1,
            nombre_billets=TAILLE_LOT,
            montant_brut_centimes=montant_brut,
            commission_centimes=commission,
            montant_talent_centimes=(
                montant_brut - commission
            ),
            devise=disponibles[0].devise,
        )

        BilletUnitePayeeAfroFans.objects.filter(
            pk__in=[item.pk for item in disponibles],
            lot__isnull=True,
        ).update(lot=lot)

        nouveaux_lots.append(lot)

    return nouveaux_lots
