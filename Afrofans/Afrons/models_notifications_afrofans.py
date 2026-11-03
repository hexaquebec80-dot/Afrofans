from django.conf import settings
from django.db import models


class NotificationOfficielleAfroFans(models.Model):

    TYPES = [
        ("evenement_fan", "Événement disponible"),
        ("frais_confirmes", "Frais confirmés"),
        ("evenement_publie", "Événement publié"),
    ]

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_officielles_afrofans",
    )

    evenement = models.ForeignKey(
        "Afrons.Evenement",
        on_delete=models.CASCADE,
        related_name="notifications_officielles",
    )

    type_notification = models.CharField(
        max_length=30,
        choices=TYPES,
    )

    titre = models.CharField(max_length=180)
    contenu = models.TextField(max_length=1000)
    est_lue = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "destinataire",
                    "evenement",
                    "type_notification",
                ],
                name="afrofans_unique_notification_par_evenement",
            )
        ]

        indexes = [
            models.Index(
                fields=["destinataire", "est_lue"]
            )
        ]


class PaiementStripeEvenementAfroFans(models.Model):

    paiement = models.ForeignKey(
        "Afrons.PaiementFraisEvenement",
        on_delete=models.CASCADE,
        related_name="checkouts_afrofans",
    )

    stripe_session_id = models.CharField(
        max_length=255,
        unique=True,
    )

    montant_cents = models.PositiveIntegerField()

    taux_xof_cad = models.DecimalField(
        max_digits=18,
        decimal_places=10,
    )

    base_cad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tps_cad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tvq_cad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    statut = models.CharField(
        max_length=20,
        default="en_attente",
    )

    cree_le = models.DateTimeField(auto_now_add=True)
    paye_le = models.DateTimeField(
        null=True,
        blank=True,
    )