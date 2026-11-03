from django.conf import settings
from django.core.mail import send_mass_mail
from django.db import transaction

from .models import (
    Abonnement,
    NotificationEvenement,
)


@transaction.atomic
def notifier_publication_evenement(
    evenement,
):
    if evenement.notifications_envoyees:
        return 0

    abonnements = (
        Abonnement.objects
        .filter(
            createur=evenement.createur,
        )
        .select_related("fan")
    )

    notifications = []
    courriels = []

    nom_createur = (
        evenement.createur.profil.nom_public
    )

    url_evenement = (
        f"{settings.SITE_URL}"
        f"{evenement.get_absolute_url()}"
    )

    for abonnement in abonnements:
        fan = abonnement.fan

        notifications.append(
            NotificationEvenement(
                destinataire=fan,
                evenement=evenement,
                titre=(
                    f"{nom_createur} annonce "
                    "un événement"
                ),
                message=(
                    f"Votre talent {nom_createur} "
                    f"organise « {evenement.titre} » "
                    f"le "
                    f"{evenement.date_evenement:%d/%m/%Y à %H:%M}, "
                    f"à {evenement.lieu}, "
                    f"{evenement.ville}. "
                    f"Prix : {evenement.prix} "
                    f"{evenement.devise}."
                ),
            )
        )

        if fan.email:
            courriels.append(
                (
                    (
                        f"Nouvel événement de "
                        f"{nom_createur}"
                    ),
                    (
                        f"Bonjour {fan.username},\n\n"
                        f"Votre talent {nom_createur} "
                        f"organise un nouvel événement.\n\n"
                        f"Titre : {evenement.titre}\n"
                        f"Date : "
                        f"{evenement.date_evenement:%d/%m/%Y à %H:%M}\n"
                        f"Lieu : {evenement.lieu}, "
                        f"{evenement.ville}\n"
                        f"Prix : {evenement.prix} "
                        f"{evenement.devise}\n\n"
                        f"Voir l’événement : "
                        f"{url_evenement}\n\n"
                        f"AfroFans, une plateforme "
                        f"de HexaQuébec."
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [fan.email],
                )
            )

    NotificationEvenement.objects.bulk_create(
        notifications,
        ignore_conflicts=True,
    )

    if courriels:
        send_mass_mail(
            courriels,
            fail_silently=True,
        )

    evenement.notifications_envoyees = True

    evenement.save(
        update_fields=[
            "notifications_envoyees",
            "modifie_le",
        ]
    )

    return len(notifications)