
import secrets
import uuid
from hashlib import sha256

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone


def generer_code_evenement():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return "AF-" + "".join(
        secrets.choice(alphabet)
        for _ in range(10)
    )


class HabilitationBilletterie(models.Model):

    TYPES = [
        ("talent", "Talent"),
        ("organisateur", "Organisateur"),
    ]

    STATUTS = [
        ("en_attente", "En attente"),
        ("verifie", "Vérifié"),
        ("suspendu", "Suspendu"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habilitation_billetterie",
    )

    type_vendeur = models.CharField(
        max_length=20,
        choices=TYPES,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    verifie_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.get_statut_display()}"
        )


class CodeAccesEvenement(models.Model):

    evenement = models.OneToOneField(
        "Evenement",
        on_delete=models.CASCADE,
        related_name="acces_controle",
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        default=generer_code_evenement,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"Code privé événement "
            f"#{self.evenement_id}"
        )


class ControleurEvenement(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.CASCADE,
        related_name="controleurs",
    )

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    pays = models.CharField(max_length=100)

    email = models.EmailField()

    actif = models.BooleanField(default=True)

    ajoute_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["prenom", "nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["evenement", "email"],
                name="unique_controleur_evenement",
            )
        ]

    def __str__(self):
        return (
            f"{self.prenom} {self.nom} "
            f"- {self.evenement.titre}"
        )


class InvitationControleur(models.Model):

    controleur = models.OneToOneField(
        ControleurEvenement,
        on_delete=models.CASCADE,
        related_name="invitation",
    )

    empreinte_jeton = models.CharField(
        max_length=64
    )

    expire_le = models.DateTimeField()

    utilise_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    def jeton_est_valide(self, jeton):
        empreinte = sha256(
            jeton.encode("utf-8")
        ).hexdigest()

        return (
            bool(jeton)
            and self.utilise_le is None
            and self.expire_le > timezone.now()
            and secrets.compare_digest(
                self.empreinte_jeton,
                empreinte,
            )
        )


class ReservationExpiration(models.Model):

    billet = models.OneToOneField(
        "BilletEvenement",
        on_delete=models.CASCADE,
        related_name="blocage_places",
    )

    expire_le = models.DateTimeField(
        db_index=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )


class BilletAcces(models.Model):

    STATUTS = [
        ("actif", "Actif"),
        ("utilise", "Utilisé"),
        ("annule", "Annulé"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.CASCADE,
        related_name="billets_acces",
    )

    reservation = models.ForeignKey(
        "BilletEvenement",
        on_delete=models.CASCADE,
        related_name="billets_individuels",
    )

    prenom_participant = models.CharField(
        max_length=100,
        blank=True,
    )

    nom_participant = models.CharField(
        max_length=100,
        blank=True,
    )

    statut = models.CharField(
        max_length=10,
        choices=STATUTS,
        default="actif",
    )

    utilise_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    controleur_entree = models.ForeignKey(
        ControleurEvenement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["evenement", "statut"]
            )
        ]

    @property
    def nom_affiche(self):
        nom = (
            f"{self.prenom_participant} "
            f"{self.nom_participant}"
        ).strip()

        return nom or "Participant non renseigné"

    def jeton_qr(self):
        return signing.dumps(
            {
                "ticket_id": str(self.pk),
                "event_id": self.evenement_id,
            },
            salt="afrofans-ticket-v1",
        )

    def __str__(self):
        return (
            f"{self.nom_affiche} "
            f"- {self.evenement.titre}"
        )


class HistoriqueScan(models.Model):

    billet = models.ForeignKey(
        BilletAcces,
        on_delete=models.CASCADE,
        related_name="historique_scans",
    )

    controleur = models.ForeignKey(
        ControleurEvenement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    resultat = models.CharField(max_length=30)

    scanne_le = models.DateTimeField(
        auto_now_add=True,
    )
