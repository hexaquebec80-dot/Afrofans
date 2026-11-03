from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Evenement
from .models_notifications_afrofans import (
    NotificationOfficielleAfroFans,
)


def notifier_frais_payes(evenement_id):

    evenement = Evenement.objects.select_related(
        "createur"
    ).get(pk=evenement_id)

    if not evenement.frais_billetterie_payes:
        return

    NotificationOfficielleAfroFans.objects.get_or_create(
        destinataire=evenement.createur,
        evenement=evenement,
        type_notification="frais_confirmes",
        defaults={
            "titre": "HexaQuébec · Paiement confirmé",
            "contenu": (
                f"Les frais de billetterie pour "
                f"« {evenement.titre} » sont confirmés. "
                "Votre événement est maintenant "
                "en attente de validation par AfroFans."
            ),
        },
    )


def annoncer_evenement_aux_fans(evenement_id):

    with transaction.atomic():

        evenement = (
            Evenement.objects
            .select_for_update()
            .select_related("createur")
            .get(pk=evenement_id)
        )

        # Aucun message avant paiement ET publication.
        if not (
            evenement.frais_billetterie_payes
            and evenement.statut in ("publie", "ouvert")
        ):
            return 0

        # Empêcher l'envoi plusieurs fois.
        if evenement.notifications_envoyees:
            return 0

        talent = (
            evenement.createur.get_full_name().strip()
            or evenement.createur.get_username()
        )

        Utilisateur = get_user_model()

        fans = (
            Utilisateur.objects
            .filter(
                profil__type_compte="fan",
                is_active=True,
            )
            .exclude(pk=evenement.createur_id)
            .values_list("pk", flat=True)
        )

        notifications = []
        total = 0

        for fan_id in fans.iterator(chunk_size=500):

            notifications.append(
                NotificationOfficielleAfroFans(
                    destinataire_id=fan_id,
                    evenement=evenement,
                    type_notification="evenement_fan",
                    titre=(
                        f"Événement disponible · "
                        f"{evenement.titre}"
                    )[:180],
                    contenu=(
                        "Message officiel HexaQuébec : "
                        f"le talent {talent} annonce "
                        f"son événement « {evenement.titre} ». "
                        "Les billets sont disponibles. "
                        "Achetez votre billet pour participer "
                        "à cet événement AfroFans."
                    )[:1000],
                )
            )

            if len(notifications) >= 500:

                NotificationOfficielleAfroFans.objects.bulk_create(
                    notifications,
                    batch_size=500,
                    ignore_conflicts=True,
                )

                total += len(notifications)
                notifications = []

        if notifications:

            NotificationOfficielleAfroFans.objects.bulk_create(
                notifications,
                batch_size=500,
                ignore_conflicts=True,
            )

            total += len(notifications)

        # Notification envoyée au talent.
        NotificationOfficielleAfroFans.objects.get_or_create(
            destinataire=evenement.createur,
            evenement=evenement,
            type_notification="evenement_publie",
            defaults={
                "titre": (
                    "HexaQuébec · Votre événement est publié"
                ),
                "contenu": (
                    f"Votre événement « {evenement.titre} » "
                    "est maintenant publié sur AfroFans. "
                    "Les fans peuvent le consulter et "
                    "réserver leurs billets."
                ),
            },
        )

        Evenement.objects.filter(
            pk=evenement.pk
        ).update(
            notifications_envoyees=True
        )

        return total