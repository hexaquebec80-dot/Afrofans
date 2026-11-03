from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Evenement
from .services_notifications_afrofans import (
    annoncer_evenement_aux_fans,
)


@receiver(
    post_save,
    sender=Evenement,
    dispatch_uid="afrofans_publication_notification",
)
def declencher_annonce_evenement(sender, instance, **kwargs):

    if (
        instance.frais_billetterie_payes
        and instance.statut in ("publie", "ouvert")
        and not instance.notifications_envoyees
    ):

        evenement_id = instance.pk

        transaction.on_commit(
            lambda: annoncer_evenement_aux_fans(
                evenement_id
            )
        )