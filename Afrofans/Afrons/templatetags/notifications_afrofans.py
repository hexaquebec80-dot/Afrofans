from django import template
from django.urls import reverse, NoReverseMatch

from Afrons.models import PaiementFraisEvenement
from Afrons.models_notifications_afrofans import (
    NotificationOfficielleAfroFans,
)


register = template.Library()


@register.inclusion_tag(
    "Afrons/partials/notifications_afrofans.html",
    takes_context=True,
)
def notifications_afrofans(context):

    request = context.get("request")
    personne = context.get("personne")

    if not request or not request.user.is_authenticated:
        return {"autorise": False}

    # Ne pas afficher les notifications privées
    # lorsqu'on visite le profil d'une autre personne.
    if personne and personne.pk != request.user.pk:
        return {"autorise": False}

    notifications = (
        NotificationOfficielleAfroFans.objects
        .filter(destinataire=request.user)
        .select_related(
            "evenement",
            "evenement__createur",
        )
    )

    return {
        "autorise": True,
        "notifications_officielles": notifications[:20],
        "total_non_lues": notifications.filter(
            est_lue=False
        ).count(),
    }


@register.simple_tag
def url_paiement_evenement(evenement):

    if evenement.frais_billetterie_payes:
        return ""

    paiement = (
        PaiementFraisEvenement.objects
        .filter(evenement=evenement)
        .exclude(statut="paye")
        .order_by("-pk")
        .first()
    )

    if not paiement:
        return ""

    try:
        return reverse(
            "Afrons:payer_frais_evenement",
            kwargs={"paiement_id": paiement.pk},
        )
    except NoReverseMatch:
        return ""