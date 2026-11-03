
from django.conf import settings
from django.db import models


class CertificationCompteAfroFans(models.Model):

    STATUTS = [
        ("non_certifie", "Non certifié"),
        ("en_verification", "En attente de vérification"),
        ("certifie", "Compte certifié"),
    ]

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certification_compte_afrofans",
    )

    statut = models.CharField(
        max_length=30,
        choices=STATUTS,
        default="non_certifie",
    )

    paiement_confirme = models.BooleanField(
        default=False,
    )

    certifie_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Certification AfroFans"
        verbose_name_plural = "Certifications AfroFans"

    def __str__(self):
        return (
            f"{self.utilisateur} - "
            f"{self.get_statut_display()}"
        )


class PaiementCertificationAfroFans(models.Model):

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paiements_certification_afrofans",
    )

    stripe_session_id = models.CharField(
        max_length=255,
        unique=True,
    )

    montant_base_centimes = models.PositiveIntegerField(
        default=1500,
    )

    statut = models.CharField(
        max_length=30,
        default="en_attente",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    paye_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"Certification {self.utilisateur} "
            f"- {self.statut}"
        )
