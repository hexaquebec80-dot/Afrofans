from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from cloudinary_storage.storage import VideoMediaCloudinaryStorage

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse
import uuid
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.conf import settings
from django.core.validators import MinValueValidator

from django.urls import reverse
import uuid

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from decimal import (

    ROUND_CEILING,
)

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone


from .storage import AfroFansVideoStorage











class Profil(models.Model):

    TYPES_COMPTES = [
        ("fan", "Fan"),
        ("createur", "Créateur"),
    ]

    PAYS_AUTORISES = [
        ("ML", "Mali (+223)"),
        ("CI", "Côte d’Ivoire (+225)"),
        ("SN", "Sénégal (+221)"),
        ("CA", "Canada (+1)"),
        ("FR", "France (+33)"),
    ]

    INDICATIFS_PAYS = {
        "ML": "+223",
        "CI": "+225",
        "SN": "+221",
        "CA": "+1",
        "FR": "+33",
    }

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profil",
    )

    type_compte = models.CharField(
        max_length=20,
        choices=TYPES_COMPTES,
        default="fan",
    )

    nom_scene = models.CharField(
        max_length=100,
        blank=True,
    )

    biographie = models.CharField(
        max_length=250,
        blank=True,
    )

    # La photo est facultative à l’inscription.
    # Elle sera ajoutée plus tard depuis le profil.
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
    )

    pays = models.CharField(
        max_length=2,
        choices=PAYS_AUTORISES,
        blank=True,
    )

    numero_telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text=(
            "Ton numéro reste privé. "
            "Il n’apparaît jamais sur ton profil public."
        ),
    )

    ville = models.CharField(
        max_length=100,
        blank=True,
    )

    est_certifie = models.BooleanField(
        default=False,
        help_text=(
            "Talent vérifié par HexaQuébec."
        ),
    )

    telephone_verifie = models.BooleanField(
        default=False,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-cree_le",
        ]

        verbose_name = "Profil"

        verbose_name_plural = "Profils"

    @property
    def nom_public(self):
        nom_scene = (
            self.nom_scene
            or ""
        ).strip()

        nom_complet = (
            self.utilisateur
            .get_full_name()
            .strip()
        )

        return (
            nom_scene
            or nom_complet
            or self.utilisateur.username
        )

    @property
    def indicatif_pays(self):
        return self.INDICATIFS_PAYS.get(
            self.pays,
            "",
        )

    @property
    def est_createur(self):
        return (
            self.type_compte
            == "createur"
        )

    @property
    def est_fan(self):
        return (
            self.type_compte
            == "fan"
        )

    @property
    def peut_publier_video(self):
        return self.est_createur

    @property
    def peut_recevoir_don(self):
        return self.est_createur

    def clean(self):
        super().clean()

        erreurs = {}

        self.nom_scene = (
            self.nom_scene
            or ""
        ).strip()

        self.biographie = (
            self.biographie
            or ""
        ).strip()

        self.ville = (
            self.ville
            or ""
        ).strip()

        pays = (
            self.pays
            or ""
        ).strip().upper()

        self.pays = pays

        telephone = (
            self.numero_telephone
            or ""
        )

        telephone = (
            telephone
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
        )

        if (
            pays
            and pays
            not in self.INDICATIFS_PAYS
        ):
            erreurs["pays"] = (
                "Ce pays n’est pas encore "
                "accepté sur AfroFans."
            )

        if telephone:
            if not telephone.startswith("+"):
                erreurs["numero_telephone"] = (
                    "Ajoute l’indicatif du pays. "
                    "Exemple : +22370000000."
                )

            elif not telephone[1:].isdigit():
                erreurs["numero_telephone"] = (
                    "Le numéro doit contenir "
                    "uniquement des chiffres après le +."
                )

            elif (
                len(telephone[1:]) < 8
                or len(telephone[1:]) > 15
            ):
                erreurs["numero_telephone"] = (
                    "Le numéro de téléphone "
                    "n’est pas valide."
                )

            elif pays:
                indicatif = (
                    self.INDICATIFS_PAYS.get(
                        pays,
                        "",
                    )
                )

                if (
                    indicatif
                    and not telephone.startswith(
                        indicatif
                    )
                ):
                    erreurs["numero_telephone"] = (
                        "Pour ce pays, le numéro "
                        f"doit commencer par {indicatif}."
                    )

        if self.type_compte == "createur":
            if not self.nom_scene:
                erreurs["nom_scene"] = (
                    "Le nom de scène est obligatoire "
                    "pour un créateur."
                )

            if not pays:
                erreurs["pays"] = (
                    "Le pays est obligatoire "
                    "pour un créateur."
                )

            if not telephone:
                erreurs["numero_telephone"] = (
                    "Le numéro de téléphone est "
                    "obligatoire pour un créateur."
                )

            # Aucune validation obligatoire
            # concernant l’avatar ici.

        self.numero_telephone = (
            telephone or None
        )

        if erreurs:
            raise ValidationError(
                erreurs
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return self.nom_public




# ============================================================
# AFROFANS — MODÈLE VIDÉO
# PostgreSQL + Cloudinary
# Vidéos originales et vidéos traitées
# ============================================================

class Video(models.Model):

    # =====================================================
    # CATÉGORIES
    # =====================================================

    CATEGORIES = [
        ("musique", "Musique"),
        ("danse", "Danse"),
        ("humour", "Humour"),
        ("mode", "Mode"),
        ("cuisine", "Cuisine"),
        ("sport", "Sport"),
        ("art", "Art"),
        ("culture", "Culture"),
        ("education", "Éducation"),
        ("autre", "Autre"),
    ]

    # =====================================================
    # FILTRES DE COULEUR
    # =====================================================

    FILTRES_COULEUR = [
        ("natural", "Naturel"),
        ("warm", "Chaleur"),
        ("cinema", "Cinéma"),
        ("vibrant", "Vibrant"),
        ("gold", "Or africain"),
        ("mono", "Monochrome"),
    ]

    # =====================================================
    # STATUTS DE TRAITEMENT
    # =====================================================

    STATUTS_TRAITEMENT = [
        (
            "non_requis",
            "Aucun traitement",
        ),
        (
            "en_attente",
            "En attente",
        ),
        (
            "traitement",
            "Traitement en cours",
        ),
        (
            "termine",
            "Traitement terminé",
        ),
        (
            "echec",
            "Échec du traitement",
        ),
    ]

    # =====================================================
    # AUTEUR
    # =====================================================

    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="videos",
    )

    # =====================================================
    # INFORMATIONS DE LA VIDÉO
    # =====================================================

    titre = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        max_length=1500,
        blank=True,
    )

    # =====================================================
    # VIDÉO ORIGINALE — CLOUDINARY
    # =====================================================

    fichier = models.FileField(
        upload_to="videos/originales/%Y/%m/",

        storage=VideoMediaCloudinaryStorage(),

        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "mp4",
                    "webm",
                    "mov",
                ]
            )
        ],

        help_text=(
            "Vidéo originale au format "
            "MP4, WebM ou MOV."
        ),
    )

    # =====================================================
    # VIDÉO TRAITÉE — CLOUDINARY / AFROFANS STUDIO
    # =====================================================

    fichier_traite = models.FileField(
        upload_to="videos/traitees/%Y/%m/",

        storage=VideoMediaCloudinaryStorage(),

        blank=True,
        null=True,
        editable=False,

        help_text=(
            "Version créée automatiquement "
            "par AfroFans Studio."
        ),
    )

    # =====================================================
    # MINIATURE — CLOUDINARY IMAGE
    # =====================================================

    miniature = models.ImageField(
        upload_to="miniatures/%Y/%m/",
        blank=True,
        null=True,
    )

    # =====================================================
    # CATÉGORIE ET HASHTAGS
    # =====================================================

    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIES,
        default="autre",
        db_index=True,
    )

    hashtags = models.CharField(
        max_length=300,
        blank=True,

        help_text=(
            "Exemple : #musique #mali #afrique"
        ),
    )

    # =====================================================
    # MUSIQUE AFROFANS
    # =====================================================

    musique = models.ForeignKey(
        "Musique",
        on_delete=models.SET_NULL,
        related_name="videos",
        blank=True,
        null=True,

        help_text=(
            "Musique autorisée ajoutée "
            "à la vidéo."
        ),
    )

    volume_musique = models.PositiveSmallIntegerField(
        default=70,

        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],

        help_text=(
            "Volume de la musique entre 0 et 100."
        ),
    )

    volume_original = models.PositiveSmallIntegerField(
        default=100,

        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],

        help_text=(
            "Volume du son original entre 0 et 100."
        ),
    )

    # =====================================================
    # FILTRES ET COULEURS
    # =====================================================

    filtre_couleur = models.CharField(
        max_length=20,
        choices=FILTRES_COULEUR,
        default="natural",
    )

    luminosite = models.PositiveSmallIntegerField(
        default=100,

        validators=[
            MinValueValidator(60),
            MaxValueValidator(140),
        ],

        help_text=(
            "Luminosité entre 60 et 140."
        ),
    )

    contraste = models.PositiveSmallIntegerField(
        default=100,

        validators=[
            MinValueValidator(60),
            MaxValueValidator(160),
        ],

        help_text=(
            "Contraste entre 60 et 160."
        ),
    )

    saturation = models.PositiveSmallIntegerField(
        default=100,

        validators=[
            MinValueValidator(0),
            MaxValueValidator(200),
        ],

        help_text=(
            "Saturation entre 0 et 200."
        ),
    )

    # =====================================================
    # TRAITEMENT FFMPEG
    # =====================================================

    statut_traitement = models.CharField(
        max_length=20,
        choices=STATUTS_TRAITEMENT,
        default="non_requis",
        db_index=True,
        editable=False,
    )

    erreur_traitement = models.TextField(
        blank=True,
        editable=False,
    )

    traite_le = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )

    # =====================================================
    # PUBLICATION
    # =====================================================

    est_publiee = models.BooleanField(
        default=True,
        db_index=True,
    )

    est_a_la_une = models.BooleanField(
        default=False,
        db_index=True,
    )

    autoriser_commentaires = models.BooleanField(
        default=True,
    )

    # =====================================================
    # STATISTIQUES
    # =====================================================

    vues = models.PositiveBigIntegerField(
        default=0,
    )

    nombre_partages = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de partages",
    )

    # =====================================================
    # DATES
    # =====================================================

    creee_le = models.DateTimeField(
        auto_now_add=True,
    )

    modifiee_le = models.DateTimeField(
        auto_now=True,
    )

    # =====================================================
    # CONFIGURATION DU MODÈLE
    # =====================================================

    class Meta:

        ordering = [
            "-est_a_la_une",
            "-creee_le",
        ]

        indexes = [
            models.Index(
                fields=[
                    "est_publiee",
                    "-creee_le",
                ],
                name="video_publication_idx",
            ),

            models.Index(
                fields=[
                    "categorie",
                    "-creee_le",
                ],
                name="video_categorie_idx",
            ),
        ]

        verbose_name = "Vidéo"
        verbose_name_plural = "Vidéos"

    # =====================================================
    # VIDÉO À DIFFUSER
    # =====================================================

    @property
    def fichier_diffuse(self):
        """
        Retourne la vidéo traitée lorsqu'elle est prête.
        Sinon, retourne la vidéo originale.
        """

        if (
            self.statut_traitement == "termine"
            and self.fichier_traite
        ):
            return self.fichier_traite

        return self.fichier

    # =====================================================
    # TRAITEMENT RÉUSSI
    # =====================================================

    @property
    def traitement_reussi(self):

        return (
            self.statut_traitement == "termine"
            and bool(self.fichier_traite)
        )

    # =====================================================
    # TRAITEMENT EN COURS
    # =====================================================

    @property
    def traitement_en_cours(self):

        return self.statut_traitement in (
            "en_attente",
            "traitement",
        )

    # =====================================================
    # UTILISATION DE MUSIQUE
    # =====================================================

    @property
    def utilise_musique(self):

        return bool(
            self.musique_id
            and self.volume_musique > 0
        )

    # =====================================================
    # NOM DE LA MUSIQUE
    # =====================================================

    @property
    def nom_musique(self):

        if self.musique_id:
            return self.musique.titre

        return "Son original"

    # =====================================================
    # URL DE LA VIDÉO
    # =====================================================

    def get_absolute_url(self):

        return reverse(
            "Afrons:detail_video",
            args=[
                self.pk,
            ],
        )

    # =====================================================
    # REPRÉSENTATION
    # =====================================================

    def __str__(self):
        return self.titre


class Musique(models.Model):

    GENRES = [
        ("afrobeat", "Afrobeat"),
        ("afropop", "Afropop"),
        ("mandingue", "Mandingue"),
        ("coupe_decale", "Coupé-décalé"),
        ("rap", "Rap"),
        ("rnb", "R&B"),
        ("gospel", "Gospel"),
        ("instrumental", "Instrumental"),
        ("traditionnel", "Traditionnel"),
        ("autre", "Autre"),
    ]

    titre = models.CharField(
        max_length=160,
    )

    artiste = models.CharField(
        max_length=160,
    )

    fichier = models.FileField(
        upload_to="musiques/%Y/%m/",
    )

    couverture = models.ImageField(
        upload_to="musiques/couvertures/%Y/%m/",
        blank=True,
        null=True,
    )

    genre = models.CharField(
        max_length=30,
        choices=GENRES,
        default="afrobeat",
        db_index=True,
    )

    duree_secondes = models.PositiveIntegerField(
        default=30,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(600),
        ],
    )

    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="musiques_ajoutees",
        blank=True,
        null=True,
    )

    est_autorisee = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "HexaQuébec confirme que cette musique "
            "peut être utilisée sur AfroFans."
        ),
    )

    est_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    est_populaire = models.BooleanField(
        default=False,
        db_index=True,
    )

    nombre_utilisations = models.PositiveIntegerField(
        default=0,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    modifie_le = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-est_populaire",
            "-nombre_utilisations",
            "titre",
        ]

        verbose_name = "Musique"
        verbose_name_plural = "Musiques"

    @property
    def duree_formatee(self):
        minutes = self.duree_secondes // 60
        secondes = self.duree_secondes % 60

        return f"{minutes}:{secondes:02d}"

    def __str__(self):
        return f"{self.titre} — {self.artiste}"













class Abonnement(models.Model):

    fan = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="abonnements",
    )

    createur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="abonnes",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fan", "createur"],
                name="abonnement_unique",
            )
        ]

    def __str__(self):
        return f"{self.fan} suit {self.createur}"


class Jaime(models.Model):

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="jaimes",
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="jaimes",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["utilisateur", "video"],
                name="jaime_unique",
            )
        ]

    def __str__(self):
        return f"{self.utilisateur} aime {self.video}"


class Favori(models.Model):

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favoris",
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="favoris",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["utilisateur", "video"],
                name="favori_unique",
            )
        ]

    def __str__(self):
        return f"{self.video} enregistré par {self.utilisateur}"


class Commentaire(models.Model):

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="commentaires",
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="commentaires",
    )

    contenu = models.CharField(
        max_length=500,
    )

    est_visible = models.BooleanField(
        default=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    reponse_a = models.ForeignKey(
    "self",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="reponses",
    )

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return f"Commentaire de {self.utilisateur}"




# ============================================================
# AFROFANS — J'AIME SUR LES COMMENTAIRES
# ============================================================

class JaimeCommentaire(models.Model):

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jaimes_commentaires",
    )

    commentaire = models.ForeignKey(
        "Commentaire",
        on_delete=models.CASCADE,
        related_name="jaimes_commentaires",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["utilisateur", "commentaire"],
                name="af_jaime_commentaire_unique",
            ),
        ]


# ============================================================
# AFROFANS — SIGNALEMENT DES COMMENTAIRES
# ============================================================

class SignalementCommentaire(models.Model):

    MOTIFS = [
        ("violence", "Violence ou menace"),
        ("haine", "Haine ou discrimination"),
        ("harcelement", "Harcèlement"),
        ("spam", "Spam ou publicité"),
        ("nudite", "Contenu sexuel"),
        ("arnaque", "Arnaque"),
        ("autre", "Autre"),
    ]

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signalements_commentaires",
    )

    commentaire = models.ForeignKey(
        "Commentaire",
        on_delete=models.CASCADE,
        related_name="signalements_recus",
    )

    motif = models.CharField(
        max_length=30,
        choices=MOTIFS,
    )

    details = models.TextField(
        max_length=500,
        blank=True,
    )

    traite = models.BooleanField(
        default=False,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["auteur", "commentaire"],
                name="af_signalement_commentaire_unique",
            ),
        ]





class Signalement(models.Model):

    RAISONS = [
        ("contenu", "Contenu inapproprié"),
        ("violence", "Violence"),
        ("haine", "Haine ou harcèlement"),
        ("nudite", "Nudité"),
        ("spam", "Spam ou arnaque"),
        ("droits", "Atteinte aux droits"),
        ("autre", "Autre"),
    ]

    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="signalements",
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="signalements",
    )

    raison = models.CharField(
        max_length=30,
        choices=RAISONS,
    )

    details = models.TextField(
        max_length=500,
        blank=True,
    )

    traite = models.BooleanField(
        default=False,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["auteur", "video"],
                name="signalement_unique",
            )
        ]

    def __str__(self):
        return f"Signalement : {self.video}"






class Don(models.Model):

    DEVISES = [
        ("XOF", "FCFA"),
        ("CAD", "Dollar canadien"),
        ("EUR", "Euro"),
    ]

    METHODES_PAIEMENT = [
        ("orange_money", "Orange Money"),
        ("interac", "Virement Interac"),
        ("carte", "Carte bancaire"),
    ]

    STATUTS = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("echoue", "Échoué"),
        ("rembourse", "Remboursé"),
    ]

    donateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dons_envoyes",
    )

    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dons_recus",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(1)
        ],
    )

    devise = models.CharField(
        max_length=3,
        choices=DEVISES,
        default="XOF",
    )

    methode_paiement = models.CharField(
        max_length=30,
        choices=METHODES_PAIEMENT,
    )

    message = models.CharField(
        max_length=300,
        blank=True,
    )

    anonyme = models.BooleanField(
        default=False,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    reference = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    modifie_le = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return (
            f"{self.montant} {self.devise} "
            f"pour {self.createur.username}"
        )




class Evenement(models.Model):

    DEVISES = Don.DEVISES

    STATUTS = [
        ("brouillon", "Brouillon"),
        ("paiement_attente", "Paiement des frais en attente"),
        ("en_attente", "En attente de validation"),
        ("publie", "Publié"),
        ("ouvert", "Événement ouvert"),
        ("refuse", "Refusé"),
        ("annule", "Annulé"),
        ("termine", "Terminé"),
    ]

    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evenements",
    )

    titre = models.CharField(max_length=160)
    description = models.TextField(max_length=3000)

    affiche = models.ImageField(
        upload_to="evenements/affiches/%Y/%m/"
    )

    lieu = models.CharField(max_length=180)
    adresse = models.CharField(max_length=250, blank=True)
    ville = models.CharField(max_length=100)

    pays = models.CharField(
        max_length=2,
        choices=Profil.PAYS_AUTORISES,
    )

    date_evenement = models.DateTimeField()

    prix = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
        verbose_name="Prix d'un billet",
    )

    devise = models.CharField(
        max_length=3,
        choices=DEVISES,
        default="XOF",
    )

    nombre_places = models.PositiveIntegerField(
        default=10,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100),
        ],
        verbose_name="Nombre de billets",
    )

    statut = models.CharField(
        max_length=25,
        choices=STATUTS,
        default="brouillon",
    )

    frais_billetterie_payes = models.BooleanField(
        default=False
    )

    frais_payes_le = models.DateTimeField(
        null=True,
        blank=True,
    )

    notifications_envoyees = models.BooleanField(
        default=False
    )

    motif_refus = models.TextField(blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date_evenement"]
        verbose_name = "Événement"
        verbose_name_plural = "Événements"

    def clean(self):
        super().clean()

        erreurs = {}

        if not 1 <= self.nombre_places <= 100:
            erreurs["nombre_places"] = (
                "Le nombre de billets doit être "
                "compris entre 1 et 100."
            )

        if self.date_evenement:
            if (
                self._state.adding
                and self.date_evenement <= timezone.now()
            ):
                erreurs["date_evenement"] = (
                    "La date doit être dans le futur."
                )

        if self.prix is not None and self.prix <= 0:
            erreurs["prix"] = (
                "Le prix doit être supérieur à zéro."
            )

        if self.statut in ("publie", "ouvert"):
            if not self.frais_billetterie_payes:
                erreurs["statut"] = (
                    "Les frais de billetterie "
                    "doivent être payés."
                )

        if erreurs:
            raise ValidationError(erreurs)

    @property
    def nombre_tranches(self):
        return int(
            (
                Decimal(self.nombre_places)
                / Decimal("10")
            ).to_integral_value(
                rounding=ROUND_CEILING
            )
        )

    @property
    def frais_billetterie_ht(self):
        return (
            Decimal(self.nombre_tranches)
            * Decimal("50.00")
        )

    @property
    def montant_tps(self):
        return (
            self.frais_billetterie_ht
            * Decimal("0.05")
        ).quantize(Decimal("0.01"))

    @property
    def montant_tvq(self):
        return (
            self.frais_billetterie_ht
            * Decimal("0.09975")
        ).quantize(Decimal("0.01"))

    @property
    def total_taxes(self):
        return self.montant_tps + self.montant_tvq

    @property
    def frais_billetterie_ttc(self):
        return (
            self.frais_billetterie_ht
            + self.total_taxes
        )

    @property
    def places_vendues(self):
        resultat = self.billets.filter(
            statut="paye"
        ).aggregate(
            total=Sum("quantite")
        )

        return resultat["total"] or 0

    @property
    def places_restantes(self):
        if not self.pk:
            return self.nombre_places

        modele = self._meta.apps.get_model(
            "Afrons",
            "ReservationExpiration",
        )

        bloquees = modele.objects.filter(
            billet__evenement=self,
            billet__statut="en_attente",
            expire_le__gt=timezone.now(),
        ).aggregate(
            total=Sum("billet__quantite")
        )["total"] or 0

        return max(
            self.nombre_places
            - self.places_vendues
            - bloquees,
            0,
        )

    @property
    def places_disponibles(self):
        return self.places_restantes

    @property
    def est_complet(self):
        return self.places_restantes <= 0

    @property
    def revenu_total(self):
        resultat = self.billets.filter(
            statut="paye"
        ).aggregate(
            total=Sum("montant_total")
        )

        return resultat["total"] or Decimal("0.00")

    @property
    def est_ouvert(self):
        return self.statut == "ouvert"

    @property
    def est_termine(self):
        return self.statut == "termine"

    def get_absolute_url(self):
        return reverse(
            "Afrons:detail_evenement",
            args=[self.pk],
        )

    def __str__(self):
        return self.titre



class BilletEvenement(models.Model):

    # =========================================
    # MÉTHODES DE PAIEMENT
    # =========================================

    METHODES_PAIEMENT = [
        ("orange_money", "Orange Money"),
        ("wave", "Wave"),
        ("carte", "Carte bancaire"),
        ("interac", "Interac"),
        ("autre", "Autre"),
    ]

    # =========================================
    # STATUTS
    # =========================================

    STATUTS = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("annule", "Annulé"),
        ("rembourse", "Remboursé"),
    ]

    # =========================================
    # RELATIONS
    # =========================================

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.CASCADE,
        related_name="billets",
    )

    acheteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billets_evenements",
    )

    # =========================================
    # INFORMATIONS DU PARTICIPANT
    # =========================================

    nom_participant = models.CharField(
        max_length=150,
    )

    courriel = models.EmailField()

    quantite = models.PositiveIntegerField(
        default=1,
    )

    # =========================================
    # TARIFICATION
    # =========================================

    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    # =========================================
    # PAIEMENT
    # =========================================

    methode_paiement = models.CharField(
        max_length=30,
        choices=METHODES_PAIEMENT,
        default="orange_money",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    # =========================================
    # CODE DE RÉFÉRENCE
    # =========================================

    code_billet = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        blank=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Achat de billet"
        verbose_name_plural = "Achats de billets"

    # =========================================
    # VALIDATION
    # =========================================

    def clean(self):
        super().clean()

        erreurs = {}

        if not self.evenement_id:
            erreurs["evenement"] = (
                "Sélectionne un événement."
            )

        if (
            self.quantite is None
            or self.quantite < 1
        ):
            erreurs["quantite"] = (
                "La quantité minimale est 1."
            )

        elif self.quantite > 100:
            erreurs["quantite"] = (
                "Maximum 100 billets."
            )

        if self.evenement_id:
            if self.evenement.prix <= 0:
                erreurs["evenement"] = (
                    "Le prix doit être supérieur à zéro."
                )

        if erreurs:
            raise ValidationError(erreurs)

    # =========================================
    # ENREGISTREMENT
    # =========================================

    def save(self, *args, **kwargs):

        if not self.evenement_id:
            raise ValidationError(
                "L'événement est obligatoire."
            )

        if self._state.adding:

            self.prix_unitaire = (
                self.evenement.prix
            )

            self.montant_total = (
                self.prix_unitaire
                * Decimal(str(self.quantite))
            )

        if not self.code_billet:
            self.code_billet = uuid.uuid4().hex

        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    # =========================================
    # PROPRIÉTÉS
    # =========================================

    @property
    def est_paye(self):
        return self.statut == "paye"

    @property
    def devise(self):
        return self.evenement.devise

    def __str__(self):
        return (
            f"{self.nom_participant} - "
            f"{self.evenement.titre} - "
            f"{self.quantite} billet(s)"
        )



class DemandePublication(models.Model):

    STATUTS = [
        ("en_attente", "En attente"),
        ("approuvee", "Approuvée"),
        ("refusee", "Refusée"),
    ]

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_publication",
    )

    titre = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        max_length=1500,
        blank=True,
    )

    fichier = models.FileField(
        upload_to="demandes_publication/videos/%Y/%m/",
    )

    miniature = models.ImageField(
        upload_to="demandes_publication/miniatures/%Y/%m/",
        blank=True,
        null=True,
    )

    categorie = models.CharField(
        max_length=30,
        choices=Video.CATEGORIES,
        default="autre",
    )

    hashtags = models.CharField(
        max_length=300,
        blank=True,
    )

    message_equipe = models.TextField(
        max_length=1000,
        blank=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    motif_refus = models.TextField(
        blank=True,
    )

    video_publiee = models.OneToOneField(
        Video,
        on_delete=models.SET_NULL,
        related_name="demande_origine",
        blank=True,
        null=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    modifie_le = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return (
            f"{self.titre} - "
            f"{self.get_statut_display()}"
        )



class ControleEvenement(models.Model):

    evenement = models.OneToOneField(
        "Evenement",
        on_delete=models.CASCADE,
        related_name="controle_entree",
    )

    code_secret_hash = models.CharField(
        max_length=128,
    )

    modifie_le = models.DateTimeField(
        auto_now=True,
    )

    def definir_code_secret(
        self,
        code_secret,
    ):
        self.code_secret_hash = make_password(
            code_secret
        )

    def verifier_code_secret(
        self,
        code_secret,
    ):
        return check_password(
            code_secret,
            self.code_secret_hash,
        )

    def __str__(self):
        return (
            f"Contrôle — {self.evenement}"
        )


class TicketEntree(models.Model):

    STATUTS = [
        ("valide", "Valide"),
        ("utilise", "Utilisé"),
        ("annule", "Annulé"),
    ]

    commande = models.ForeignKey(
        "BilletEvenement",
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.PROTECT,
        related_name="tickets_entree",
    )

    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tickets_evenements",
    )

    identifiant = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    code_public = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
    )

    numero = models.PositiveIntegerField()

    nom_participant = models.CharField(
        max_length=150,
    )

    categorie = models.CharField(
        max_length=50,
        default="Standard",
    )

    rangee = models.CharField(
        max_length=20,
        blank=True,
    )

    siege = models.CharField(
        max_length=20,
        blank=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="valide",
    )

    utilise_le = models.DateTimeField(
        blank=True,
        null=True,
    )

    controle_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tickets_controles",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = (
            "commande_id",
            "numero",
        )

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "commande",
                    "numero",
                ),
                name=(
                    "ticket_numero_unique_"
                    "par_commande"
                ),
            ),
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):
        if not self.code_public:

            while True:

                code = (
                    "AFR-"
                    + secrets.token_hex(
                        8
                    ).upper()
                )

                existe = (
                    TicketEntree.objects
                    .filter(
                        code_public=code
                    )
                    .exists()
                )

                if not existe:
                    self.code_public = code
                    break

        super().save(
            *args,
            **kwargs,
        )

    @property
    def contenu_qr(self):

        return (
            f"AFROFANS:"
            f"{self.identifiant}:"
            f"{self.code_public}"
        )

    def __str__(self):

        return (
            f"{self.code_public} — "
            f"{self.evenement}"
        )


class ControleTicket(models.Model):

    RESULTATS = [
        ("accepte", "Accepté"),
        (
            "deja_utilise",
            "Déjà utilisé",
        ),
        ("annule", "Annulé"),
        ("invalide", "Invalide"),
    ]

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.CASCADE,
        related_name=(
            "historique_controles"
        ),
    )

    ticket = models.ForeignKey(
        TicketEntree,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="controles",
    )

    controleur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name=(
            "controles_effectues"
        ),
    )

    code_recu = models.CharField(
        max_length=200,
    )

    resultat = models.CharField(
        max_length=20,
        choices=RESULTATS,
    )

    controle_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = (
            "-controle_le",
        )

    def __str__(self):

        return (
            f"{self.get_resultat_display()} "
            f"— {self.evenement}"
        )





class PaiementFraisEvenement(models.Model):

    DEVISES_PAIEMENT = [
        (
            "XOF",
            "Franc CFA",
        ),
        (
            "CAD",
            "Dollar canadien",
        ),
        (
            "EUR",
            "Euro",
        ),
    ]

    STATUTS = [
        (
            "en_attente",
            "En attente",
        ),
        (
            "paye",
            "Payé",
        ),
        (
            "echoue",
            "Échoué",
        ),
        (
            "rembourse",
            "Remboursé",
        ),
    ]

    evenement = models.OneToOneField(
        Evenement,
        on_delete=models.CASCADE,
        related_name="paiement_frais",
    )

    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paiements_frais_evenements",
    )

    montant_original_xof = (
        models.DecimalField(
            max_digits=12,
            decimal_places=2,
        )
    )

    montant_tps_xof = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    montant_tvq_xof = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_xof = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    devise_paiement = models.CharField(
        max_length=3,
        choices=DEVISES_PAIEMENT,
        default="XOF",
    )

    taux_conversion = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=1,
        help_text=(
            "Valeur d’un XOF dans la devise "
            "de paiement."
        ),
    )

    total_converti = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    reference = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    paye_le = models.DateTimeField(
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        self.montant_original_xof = (
            self.evenement
            .frais_billetterie_ht
        )

        self.montant_tps_xof = (
            self.evenement.montant_tps
        )

        self.montant_tvq_xof = (
            self.evenement.montant_tvq
        )

        self.total_xof = (
            self.evenement
            .frais_billetterie_ttc
        )

        self.total_converti = (
            self.total_xof
            * self.taux_conversion
        ).quantize(
            Decimal("0.01")
        )

        if not self.reference:
            self.reference = (
                f"AFR-FRAIS-"
                f"{uuid.uuid4().hex.upper()}"
            )

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.reference} — "
            f"{self.evenement.titre}"
        )

    




class NotificationEvenement(models.Model):

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=(
            "notifications_evenements"
        ),
    )

    evenement = models.ForeignKey(
        Evenement,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    titre = models.CharField(
        max_length=180,
    )

    message = models.TextField(
        max_length=600,
    )

    est_lue = models.BooleanField(
        default=False,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-cree_le",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "destinataire",
                    "evenement",
                ],
                name=(
                    "notification_unique_"
                    "fan_evenement"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.destinataire} — "
            f"{self.evenement}"
        )




class AchatTelechargementVideo(models.Model):

    DEVISES = [
        ("XOF", "Franc CFA"),
        ("CAD", "Dollar canadien"),
        ("EUR", "Euro"),
    ]

    STATUTS = [
        ("en_attente", "En attente de paiement"),
        ("paye", "Payé"),
        ("annule", "Annulé"),
        ("rembourse", "Remboursé"),
    ]

    METHODES_PAIEMENT = [
        ("orange_money", "Orange Money"),
        ("wave", "Wave"),
        ("carte", "Carte bancaire"),
        ("interac", "Interac"),
        ("autre", "Autre"),
    ]

    PRIX_PAR_DEVISE = {
        "XOF": Decimal("50.00"),
        "CAD": Decimal("1.00"),
        "EUR": Decimal("1.00"),
    }

    acheteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achats_telechargements_videos",
    )

    video = models.ForeignKey(
        "Video",
        on_delete=models.CASCADE,
        related_name="achats_telechargements",
    )

    devise = models.CharField(
        max_length=3,
        choices=DEVISES,
        default="XOF",
    )

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    commission_afrofans = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    montant_createur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    methode_paiement = models.CharField(
        max_length=30,
        choices=METHODES_PAIEMENT,
        default="orange_money",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    reference = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        editable=False,
    )

    reference_paiement = models.CharField(
        max_length=150,
        blank=True,
    )

    nombre_telechargements = models.PositiveIntegerField(
        default=0,
    )

    dernier_telechargement = models.DateTimeField(
        blank=True,
        null=True,
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    paye_le = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-cree_le"]

        constraints = [
            models.UniqueConstraint(
                fields=["acheteur", "video", "devise"],
                name="achat_unique_video_utilisateur_devise",
            ),
        ]

        verbose_name = "Achat de téléchargement"

        verbose_name_plural = (
            "Achats de téléchargements"
        )

    def calculer_montants(self):
        prix = self.PRIX_PAR_DEVISE.get(
            self.devise
        )

        if prix is None:
            raise ValidationError(
                "Cette devise n’est pas acceptée."
            )

        self.montant_total = prix

        self.commission_afrofans = (
            prix * Decimal("0.30")
        ).quantize(
            Decimal("0.01")
        )

        self.montant_createur = (
            prix - self.commission_afrofans
        ).quantize(
            Decimal("0.01")
        )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                "AFD-"
                + uuid.uuid4().hex[:20].upper()
            )

        self.calculer_montants()

        if (
            self.statut == "paye"
            and self.paye_le is None
        ):
            self.paye_le = timezone.now()

        super().save(*args, **kwargs)

    @property
    def paiement_confirme(self):
        return self.statut == "paye"

    def get_absolute_url(self):
        return reverse(
            "Afrons:confirmation_telechargement_video",
            args=[self.pk],
        )

    def __str__(self):
        return (
            f"{self.reference} — "
            f"{self.video.titre}"
        )





from .models_billetterie import (
    HabilitationBilletterie,
    CodeAccesEvenement,
    ControleurEvenement,
    InvitationControleur,
    ReservationExpiration,
    BilletAcces,
    HistoriqueScan,
)
from .models_notifications_afrofans import (
    NotificationOfficielleAfroFans,
    PaiementStripeEvenementAfroFans,
)

from .models_certification_afrofans import (
    CertificationCompteAfroFans,
    PaiementCertificationAfroFans,
)





# ============================================================
# AFROFANS — DEMANDE DE VÉRIFICATION DES TALENTS
# ============================================================

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


# ============================================================
# AFROFANS — STOCKAGE DES DOCUMENTS DE VÉRIFICATION
# ============================================================

def chemin_document_verification(instance, filename):
    """
    Génère un chemin unique pour chaque document.

    Exemple :
    verifications_talents/UUID/nom-aleatoire.jpg

    IMPORTANT :
    Ce chemin ne garantit pas un stockage privé.
    Le stockage doit être sécurisé séparément.
    """

    extension = Path(filename).suffix.lower()

    extensions_autorisees = {
        ".jpg",
        ".jpeg",
        ".png",
        ".pdf",
    }

    if extension not in extensions_autorisees:
        raise ValidationError(
            "Format de fichier non autorisé."
        )

    identifiant = instance.identifiant

    return (
        f"verifications_talents/"
        f"{identifiant}/"
        f"{uuid.uuid4().hex}{extension}"
    )


# ============================================================
# AFROFANS — DEMANDE DE VÉRIFICATION OFFICIELLE TALENT
# ============================================================

class DemandeVerificationTalent(models.Model):

    # --------------------------------------------------------
    # STATUTS DE LA DEMANDE
    # --------------------------------------------------------

    STATUTS = [
        (
            "paiement_attente",
            "Paiement en attente"
        ),
        (
            "en_attente",
            "En attente d'examen"
        ),
        (
            "en_cours",
            "Examen en cours"
        ),
        (
            "approuvee",
            "Approuvée"
        ),
        (
            "refusee",
            "Refusée"
        ),
    ]

    # --------------------------------------------------------
    # DOCUMENTS AUTORISÉS
    # --------------------------------------------------------

    TYPES_DOCUMENTS = [
        (
            "passeport",
            "Passeport"
        ),
        (
            "carte_identite",
            "Carte nationale d'identité"
        ),
        (
            "permis_conduire",
            "Permis de conduire"
        ),
        (
            "titre_sejour",
            "Titre de séjour"
        ),
    ]

    # --------------------------------------------------------
    # IDENTIFIANT UNIQUE
    # --------------------------------------------------------

    identifiant = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    # --------------------------------------------------------
    # COMPTE TALENT
    # --------------------------------------------------------

    talent = models.ForeignKey(
        "Profil",
        on_delete=models.PROTECT,
        related_name="demandes_verification",
        limit_choices_to={
            "type_compte": "createur"
        },
    )

    # --------------------------------------------------------
    # INFORMATIONS PERSONNELLES
    # --------------------------------------------------------

    nom = models.CharField(
        max_length=150,
    )

    prenom = models.CharField(
        max_length=150,
    )

    date_naissance = models.DateField()

    pays = models.CharField(
        max_length=2,
        choices=Profil.PAYS_AUTORISES,
    )

    nationalite = models.CharField(
        max_length=100,
        blank=True,
    )

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    email = models.EmailField(
        max_length=254,
    )

    telephone = models.CharField(
        max_length=30,
    )

    # --------------------------------------------------------
    # IDENTITÉ ARTISTIQUE
    # --------------------------------------------------------

    nom_artistique = models.CharField(
        max_length=150,
        blank=True,
    )

    categorie_talent = models.CharField(
        max_length=100,
        help_text=(
            "Exemple : musique, humour, "
            "danse, cinéma, sport."
        ),
    )

    description_activite = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # LIEN PUBLIC DU TALENT
    # --------------------------------------------------------

    lien_public = models.URLField(
        max_length=500,
        blank=True,
    )

    # --------------------------------------------------------
    # DOCUMENT D'IDENTITÉ
    # --------------------------------------------------------

    type_document = models.CharField(
        max_length=30,
        choices=TYPES_DOCUMENTS,
    )

    # RECTO

    document_recto = models.FileField(
        upload_to=chemin_document_verification,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "pdf",
                ]
            )
        ],
    )

    # VERSO

    document_verso = models.FileField(
        upload_to=chemin_document_verification,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "pdf",
                ]
            )
        ],
    )

    # --------------------------------------------------------
    # PHOTO D'IDENTITÉ DU TALENT
    # --------------------------------------------------------

    photo_identite = models.ImageField(
        upload_to=chemin_document_verification,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                ]
            )
        ],
    )

    # --------------------------------------------------------
    # JUSTIFICATIFS PROFESSIONNELS
    # --------------------------------------------------------

    lien_instagram = models.URLField(
        blank=True,
    )

    lien_tiktok = models.URLField(
        blank=True,
    )

    lien_youtube = models.URLField(
        blank=True,
    )

    lien_facebook = models.URLField(
        blank=True,
    )

    site_officiel = models.URLField(
        blank=True,
    )

    justificatif_activite = models.FileField(
        upload_to=chemin_document_verification,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "pdf",
                ]
            )
        ],
    )

    # --------------------------------------------------------
    # CONSENTEMENT
    # --------------------------------------------------------

    consentement_verification = models.BooleanField(
        default=False,
    )

    # --------------------------------------------------------
    # STATUT ADMINISTRATIF
    # --------------------------------------------------------

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="paiement_attente",
        db_index=True,
    )

    # --------------------------------------------------------
    # REFUS DE VÉRIFICATION
    # --------------------------------------------------------

    motif_refus = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # COMMENTAIRES INTERNES
    # --------------------------------------------------------

    commentaire_interne = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # ADMINISTRATEUR RESPONSABLE
    # --------------------------------------------------------

    examine_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verifications_talents_examinees",
    )

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    date_soumission = models.DateTimeField(
        auto_now_add=True,
    )

    date_examen = models.DateTimeField(
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # CONFIGURATION DJANGO
    # --------------------------------------------------------

    class Meta:

        verbose_name = (
            "Demande de vérification Talent"
        )

        verbose_name_plural = (
            "Demandes de vérification des talents"
        )

        ordering = [
            "-date_soumission"
        ]

        indexes = [
            models.Index(
                fields=[
                    "talent",
                    "statut",
                ]
            ),
        ]

    # --------------------------------------------------------
    # VALIDATION DU DOSSIER
    # --------------------------------------------------------

    def clean(self):

        super().clean()

        erreurs = {}

        # Vérifier que le compte est un Talent.

        if self.talent_id:

            if self.talent.type_compte != "createur":

                erreurs["talent"] = (
                    "Seuls les comptes Talent peuvent "
                    "demander une vérification."
                )

        # Vérifier la date de naissance.

        if self.date_naissance:

            if self.date_naissance >= timezone.localdate():

                erreurs["date_naissance"] = (
                    "La date de naissance est invalide."
                )

        # Vérifier le consentement.

        if not self.consentement_verification:

            erreurs["consentement_verification"] = (
                "Vous devez accepter la déclaration "
                "pour envoyer votre dossier."
            )

        # Motif obligatoire en cas de refus.

        if self.statut == "refusee":

            if not self.motif_refus.strip():

                erreurs["motif_refus"] = (
                    "Le motif du refus est obligatoire."
                )

        if erreurs:
            raise ValidationError(erreurs)

    # --------------------------------------------------------
    # REPRÉSENTATION
    # --------------------------------------------------------

    def __str__(self):

        nom_talent = (
            self.nom_artistique
            or f"{self.prenom} {self.nom}"
        )

        return (
            f"{nom_talent} — "
            f"{self.get_statut_display()}"
        )

    # --------------------------------------------------------
    # PROPRIÉTÉS
    # --------------------------------------------------------

    @property
    def est_approuvee(self):

        return self.statut == "approuvee"

    @property
    def est_en_attente(self):

        return self.statut in [
            "paiement_attente",
            "en_attente",
        ]

    @property
    def paiement_en_attente(self):

        return self.statut == "paiement_attente"

    @property
    def est_en_cours(self):

        return self.statut == "en_cours"

    @property
    def est_refusee(self):

        return self.statut == "refusee"





class PresenceAfroFans(models.Model):

    talent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presences_afrofans"
    )

    sujet = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    url_video = models.URLField(max_length=1000, blank=True)

    est_active = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    terminee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]

    def terminer(self):
        self.est_active = False
        self.terminee_le = timezone.now()
        self.save(update_fields=["est_active", "terminee_le"])

    def __str__(self):
        return f"{self.talent.username} — {self.sujet}"


class PresenceSpectateur(models.Model):

    presence = models.ForeignKey(
        PresenceAfroFans,
        on_delete=models.CASCADE,
        related_name="spectateurs"
    )

    session_id = models.CharField(max_length=64)
    derniere_activite = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["presence", "session_id"],
                name="af_presence_spectateur_unique"
            )
        ]


class PresenceMessage(models.Model):

    TYPES = [
        ("commentaire", "Commentaire"),
        ("sticker", "Sticker"),
    ]

    STICKERS = [
        ("coeur", "❤️"),
        ("flamme", "🔥"),
        ("couronne", "👑"),
        ("applaudissement", "👏"),
        ("etoile", "⭐"),
        ("rose", "🌹"),
    ]

    presence = models.ForeignKey(
        PresenceAfroFans,
        on_delete=models.CASCADE,
        related_name="messages_presence"
    )

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    type_message = models.CharField(
        max_length=20,
        choices=TYPES,
        default="commentaire"
    )

    contenu = models.CharField(max_length=500, blank=True)
    sticker = models.CharField(
        max_length=30,
        choices=STICKERS,
        blank=True
    )

    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class PresenceJaime(models.Model):

    presence = models.ForeignKey(
        PresenceAfroFans,
        on_delete=models.CASCADE,
        related_name="jaimes_presence"
    )

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["presence", "utilisateur"],
                name="af_presence_jaime_unique"
            )
        ]







class PaiementBilletStripe(models.Model):
    STATUTS = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("annule", "Annulé"),
        ("rembourse", "Remboursé"),
    ]

    reservation = models.OneToOneField(
        "BilletEvenement",
        on_delete=models.PROTECT,
        related_name="paiement_stripe_afrofans",
    )

    montant_centimes = models.PositiveBigIntegerField()
    quantite = models.PositiveIntegerField()
    devise = models.CharField(
        max_length=3,
        default="cad",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="en_attente",
    )

    session_stripe = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    payment_intent_stripe = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    cree_le = models.DateTimeField(auto_now_add=True)
    paye_le = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Paiement #{self.pk} — {self.statut}"


class LotCommissionAfroFans(models.Model):
    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.PROTECT,
        related_name="lots_commission_afrofans",
    )

    numero_lot = models.PositiveIntegerField()

    nombre_billets = models.PositiveIntegerField(
        default=20
    )

    montant_brut_centimes = models.PositiveBigIntegerField()
    commission_centimes = models.PositiveBigIntegerField()
    montant_talent_centimes = models.PositiveBigIntegerField()

    devise = models.CharField(max_length=3)

    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evenement", "numero_lot"],
                name="af_lot_unique_par_evenement",
            ),
        ]

    def __str__(self):
        return (
            f"Événement {self.evenement_id} "
            f"— lot {self.numero_lot}"
        )


class BilletUnitePayeeAfroFans(models.Model):
    """
    Une ligne par billet individuel payé.

    Une réservation de 3 billets crée donc 3 lignes.
    Cela permet de regrouper exactement 20 billets
    même lorsque les fans achètent plusieurs billets
    dans une seule commande.
    """

    paiement = models.ForeignKey(
        "PaiementBilletStripe",
        on_delete=models.PROTECT,
        related_name="unites_payees",
    )

    evenement = models.ForeignKey(
        "Evenement",
        on_delete=models.PROTECT,
        related_name="unites_payees_afrofans",
    )

    numero_unite = models.PositiveIntegerField()

    montant_centimes = models.PositiveBigIntegerField()
    devise = models.CharField(max_length=3)

    lot = models.ForeignKey(
        "LotCommissionAfroFans",
        on_delete=models.PROTECT,
        related_name="billets",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["paiement", "numero_unite"],
                name="af_unite_unique_par_paiement",
            ),
        ]
