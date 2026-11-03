from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profil


@receiver(post_save, sender=User)
def creer_profil_utilisateur(sender, instance, created, **kwargs):

    if created:
        Profil.objects.create(
            utilisateur=instance
        )


import os

# Valeur d'un FCFA dans chaque devise.
# Laisser vide tant qu'un taux fiable
# n'a pas été configuré.

AFROFANS_XOF_TO_CAD = os.getenv(
    "AFROFANS_XOF_TO_CAD",
    "",
)

AFROFANS_XOF_TO_EUR = os.getenv(
    "AFROFANS_XOF_TO_EUR",
    "",
)