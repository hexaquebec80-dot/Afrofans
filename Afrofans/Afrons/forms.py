import re
from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import (

    Commentaire,
    DemandePublication,
    Don,
    Evenement,
    PaiementFraisEvenement,
    Profil,
    Signalement,
    Video,
)
from .models import Musique


from .models import AchatTelechargementVideo



# =========================================================
# OUTILS DE VALIDATION
# =========================================================

TYPES_IMAGES_ACCEPTES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)

TAILLE_IMAGE_MAXIMALE = 5 * 1024 * 1024
TAILLE_VIDEO_MAXIMALE = 200 * 1024 * 1024


def nettoyer_numero_telephone(numero):
    """
    Retire les espaces et les caractères de présentation.
    Exemple : +223 70-00-00-00 devient +22370000000.
    """

    if not numero:
        return ""

    return re.sub(
        r"[\s\-\(\)\.]",
        "",
        numero.strip(),
    )


def valider_image(image, nom="L’image"):
    if not image:
        return image

    content_type = getattr(
        image,
        "content_type",
        "",
    )

    if content_type not in TYPES_IMAGES_ACCEPTES:
        raise forms.ValidationError(
            f"{nom} doit être au format JPG, PNG ou WebP."
        )

    if image.size > TAILLE_IMAGE_MAXIMALE:
        raise forms.ValidationError(
            f"{nom} ne doit pas dépasser 5 Mo."
        )

    return image


# =========================================================
# INSCRIPTION
# =========================================================

class InscriptionForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="Adresse courriel",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "exemple@courriel.com",
                "autocomplete": "email",
            }
        ),
    )

    type_compte = forms.ChoiceField(
        required=True,
        choices=Profil.TYPES_COMPTES,
        initial="fan",
        label="Type de compte",
        widget=forms.Select(
            attrs={
                "class": "account-type-select",
            }
        ),
    )

    nom_scene = forms.CharField(
        required=False,
        max_length=100,
        label="Nom de scène",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Exemple : Awa Music",
                "autocomplete": "organization-title",
            }
        ),
    )

    pays = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Sélectionner un pays"),
            *Profil.PAYS_AUTORISES,
        ],
        label="Pays",
        widget=forms.Select(
            attrs={
                "class": "country-select",
            }
        ),
    )

    numero_telephone = forms.CharField(
        required=False,
        max_length=25,
        label="Numéro de téléphone",
        help_text=(
            "HexaQuébec protège tes données : "
            "ton numéro reste privé et n’apparaît "
            "jamais sur ton profil public."
        ),
        widget=forms.TextInput(
            attrs={
                "placeholder": "Exemple : 70 00 00 00",
                "autocomplete": "tel-national",
                "inputmode": "tel",
                "class": "phone-number-input",
            }
        ),
    )

    ville = forms.CharField(
        required=False,
        max_length=100,
        label="Ville",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Exemple : Bamako",
                "autocomplete": "address-level2",
            }
        ),
    )

    class Meta:
        model = User

        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "type_compte",
            "nom_scene",
            "pays",
            "numero_telephone",
            "ville",
            "password1",
            "password2",
        )

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Nom d’utilisateur",
                    "autocomplete": "username",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Prénom",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Nom",
                    "autocomplete": "family-name",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "Cette adresse courriel est déjà utilisée."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        type_compte = cleaned_data.get("type_compte")
        pays = cleaned_data.get("pays") or ""

        nom_scene = (
            cleaned_data.get("nom_scene")
            or ""
        ).strip()

        numero = nettoyer_numero_telephone(
            cleaned_data.get("numero_telephone")
        )

        indicatifs = Profil.INDICATIFS_PAYS

        if pays and pays not in indicatifs:
            self.add_error(
                "pays",
                "Ce pays n’est pas encore accepté sur AfroFans.",
            )

        if numero:
            if not numero.startswith("+"):
                if pays and pays in indicatifs:
                    numero = (
                        indicatifs[pays]
                        + numero.lstrip("0")
                    )
                else:
                    self.add_error(
                        "numero_telephone",
                        (
                            "Sélectionne le pays ou ajoute "
                            "l’indicatif international."
                        ),
                    )

            if numero and (
                not numero.startswith("+")
                or not numero[1:].isdigit()
            ):
                self.add_error(
                    "numero_telephone",
                    (
                        "Le numéro doit contenir uniquement "
                        "l’indicatif + et des chiffres."
                    ),
                )

            elif numero and not 8 <= len(numero[1:]) <= 15:
                self.add_error(
                    "numero_telephone",
                    "Le numéro de téléphone n’est pas valide.",
                )

            elif pays:
                indicatif = indicatifs.get(pays)

                if indicatif and not numero.startswith(indicatif):
                    self.add_error(
                        "numero_telephone",
                        (
                            f"Pour ce pays, le numéro doit "
                            f"commencer par {indicatif}."
                        ),
                    )

            if numero and Profil.objects.filter(
                numero_telephone=numero
            ).exists():
                self.add_error(
                    "numero_telephone",
                    (
                        "Ce numéro de téléphone est déjà "
                        "associé à un compte."
                    ),
                )

        if type_compte == "createur":
            if not nom_scene:
                self.add_error(
                    "nom_scene",
                    (
                        "Le nom de scène est obligatoire "
                        "pour un créateur."
                    ),
                )

            if not pays:
                self.add_error(
                    "pays",
                    (
                        "Le pays est obligatoire "
                        "pour un créateur."
                    ),
                )

            if not numero:
                self.add_error(
                    "numero_telephone",
                    (
                        "Le numéro de téléphone est obligatoire "
                        "pour un créateur."
                    ),
                )

        cleaned_data["nom_scene"] = nom_scene
        cleaned_data["numero_telephone"] = numero or None

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        utilisateur = super().save(
            commit=False
        )

        utilisateur.email = self.cleaned_data["email"]

        if not commit:
            return utilisateur

        utilisateur.save()

        profil = utilisateur.profil

        profil.type_compte = self.cleaned_data[
            "type_compte"
        ]

        profil.nom_scene = self.cleaned_data.get(
            "nom_scene",
            "",
        )

        profil.pays = self.cleaned_data.get(
            "pays",
            "",
        )

        profil.numero_telephone = self.cleaned_data.get(
            "numero_telephone"
        )

        profil.ville = self.cleaned_data.get(
            "ville",
            "",
        )

        # La photo est ajoutée après l’inscription
        # depuis la page de modification du profil.
        profil.save()

        return utilisateur


# =========================================================
# MODIFICATION DU COMPTE
# =========================================================

class UtilisateurForm(forms.ModelForm):

    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
        )

        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "email": "Adresse courriel",
        }

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Prénom",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Nom",
                    "autocomplete": "family-name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "exemple@courriel.com",
                    "autocomplete": "email",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        utilisateurs = User.objects.filter(
            email__iexact=email
        )

        if self.instance.pk:
            utilisateurs = utilisateurs.exclude(
                pk=self.instance.pk
            )

        if utilisateurs.exists():
            raise forms.ValidationError(
                "Cette adresse courriel est déjà utilisée."
            )

        return email


class ProfilForm(forms.ModelForm):

    class Meta:
        model = Profil

        fields = (
            "nom_scene",
            "biographie",
            "avatar",
            "pays",
            "numero_telephone",
            "ville",
        )

        labels = {
            "nom_scene": "Nom de scène",
            "biographie": "Biographie",
            "avatar": "Photo de profil",
            "pays": "Pays",
            "numero_telephone": "Numéro de téléphone",
            "ville": "Ville",
        }

        help_texts = {
            "numero_telephone": (
                "HexaQuébec protège tes données : ton numéro "
                "reste privé et n’apparaît jamais sur ton profil public."
            ),
        }

        widgets = {
            "nom_scene": forms.TextInput(
                attrs={
                    "placeholder": "Ton nom public",
                }
            ),
            "biographie": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": 250,
                    "placeholder": (
                        "Présente ton talent à la communauté."
                    ),
                }
            ),
            "avatar": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "pays": forms.Select(
                attrs={
                    "class": "country-select",
                }
            ),
            "numero_telephone": forms.TextInput(
                attrs={
                    "placeholder": "Exemple : 70 00 00 00",
                    "autocomplete": "tel-national",
                    "inputmode": "tel",
                    "class": "phone-number-input",
                }
            ),
            "ville": forms.TextInput(
                attrs={
                    "placeholder": "Ta ville",
                    "autocomplete": "address-level2",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["pays"].choices = [
            ("", "Sélectionner un pays"),
            *Profil.PAYS_AUTORISES,
        ]

    def clean_avatar(self):
        return valider_image(
            self.cleaned_data.get("avatar"),
            "La photo",
        )

    def clean(self):
        cleaned_data = super().clean()

        pays = cleaned_data.get("pays") or ""
        numero = nettoyer_numero_telephone(
            cleaned_data.get("numero_telephone")
        )

        type_compte = self.instance.type_compte
        indicatifs = Profil.INDICATIFS_PAYS

        if pays and pays not in indicatifs:
            self.add_error(
                "pays",
                "Ce pays n’est pas encore accepté sur AfroFans.",
            )

        if numero:
            if not numero.startswith("+"):
                if pays and pays in indicatifs:
                    numero = (
                        indicatifs[pays]
                        + numero.lstrip("0")
                    )
                else:
                    self.add_error(
                        "numero_telephone",
                        "Ajoute l’indicatif international.",
                    )

            if numero and (
                not numero.startswith("+")
                or not numero[1:].isdigit()
            ):
                self.add_error(
                    "numero_telephone",
                    "Le numéro de téléphone n’est pas valide.",
                )

            elif numero and not 8 <= len(numero[1:]) <= 15:
                self.add_error(
                    "numero_telephone",
                    "Le numéro de téléphone n’est pas valide.",
                )

            elif pays:
                indicatif = indicatifs.get(pays)

                if indicatif and not numero.startswith(indicatif):
                    self.add_error(
                        "numero_telephone",
                        (
                            f"Le numéro sélectionné doit "
                            f"commencer par {indicatif}."
                        ),
                    )

            profils = Profil.objects.filter(
                numero_telephone=numero
            )

            if self.instance.pk:
                profils = profils.exclude(
                    pk=self.instance.pk
                )

            if profils.exists():
                self.add_error(
                    "numero_telephone",
                    (
                        "Ce numéro de téléphone est déjà "
                        "associé à un autre compte."
                    ),
                )

        if type_compte == "createur":
            if not (
                cleaned_data.get("nom_scene")
                or ""
            ).strip():
                self.add_error(
                    "nom_scene",
                    (
                        "Le nom de scène est obligatoire "
                        "pour un créateur."
                    ),
                )

            if not pays:
                self.add_error(
                    "pays",
                    "Le pays est obligatoire.",
                )

            if not numero:
                self.add_error(
                    "numero_telephone",
                    (
                        "Le numéro de téléphone est obligatoire "
                        "pour un créateur."
                    ),
                )

        cleaned_data["numero_telephone"] = numero or None
        return cleaned_data


# =========================================================
# VIDÉOS
# =========================================================
class VideoForm(forms.ModelForm):

    class Meta:
        model = Video

        fields = (
            "fichier",
            "miniature",
            "titre",
            "description",
            "categorie",
            "hashtags",
            "autoriser_commentaires",
            "musique",
            "filtre_couleur",
            "luminosite",
            "contraste",
            "saturation",
            "volume_musique",
            "volume_original",
        )

        widgets = {
            "fichier": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        "video/mp4,"
                        "video/webm,"
                        "video/quicktime"
                    ),
                }
            ),
            "miniature": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        "image/jpeg,"
                        "image/png,"
                        "image/webp"
                    ),
                }
            ),
            "titre": forms.TextInput(
                attrs={
                    "placeholder": "Titre de la vidéo",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Présente ta vidéo à la communauté."
                    ),
                }
            ),
            "hashtags": forms.TextInput(
                attrs={
                    "placeholder": (
                        "#afrique #musique #talent"
                    ),
                }
            ),
            "musique": forms.HiddenInput(
                attrs={
                    "id": "selected-music-id",
                }
            ),
            "filtre_couleur": forms.HiddenInput(
                attrs={
                    "id": "selected-filter",
                }
            ),
            "luminosite": forms.HiddenInput(
                attrs={
                    "id": "brightness-hidden",
                }
            ),
            "contraste": forms.HiddenInput(
                attrs={
                    "id": "contrast-hidden",
                }
            ),
            "saturation": forms.HiddenInput(
                attrs={
                    "id": "saturation-hidden",
                }
            ),
            "volume_musique": forms.HiddenInput(
                attrs={
                    "id": "music-volume-hidden",
                }
            ),
            "volume_original": forms.HiddenInput(
                attrs={
                    "id": "original-volume-hidden",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["musique"].required = False

        self.fields["musique"].queryset = (
            Musique.objects.filter(
                est_active=True,
                est_autorisee=True,
            )
        )

    def clean_musique(self):
        musique = self.cleaned_data.get(
            "musique"
        )

        if not musique:
            return musique

        if (
            not musique.est_active
            or not musique.est_autorisee
        ):
            raise forms.ValidationError(
                (
                    "Cette musique n’est pas "
                    "autorisée sur AfroFans."
                )
            )

        return musique

class CommentaireForm(forms.ModelForm):

    class Meta:
        model = Commentaire

        fields = ("contenu",)

        widgets = {
            "contenu": forms.TextInput(
                attrs={
                    "placeholder": "Ajouter un commentaire...",
                    "maxlength": 500,
                    "autocomplete": "off",
                }
            ),
        }


class SignalementForm(forms.ModelForm):

    class Meta:
        model = Signalement

        fields = (
            "raison",
            "details",
        )

        widgets = {
            "details": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Explique le problème",
                }
            ),
        }


# =========================================================
# DONS
# =========================================================

class DonForm(forms.ModelForm):

    class Meta:
        model = Don

        fields = (
            "montant",
            "devise",
            "methode_paiement",
            "message",
            "anonyme",
        )

        widgets = {
            "montant": forms.NumberInput(
                attrs={
                    "min": "1",
                    "step": "0.01",
                    "placeholder": "Montant du don",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 500,
                    "placeholder": (
                        "Message destiné au créateur"
                    ),
                }
            ),
        }

    def clean_montant(self):
        montant = self.cleaned_data["montant"]

        if montant <= Decimal("0"):
            raise forms.ValidationError(
                "Le montant doit être supérieur à zéro."
            )

        return montant


# =========================================================
# ÉVÉNEMENTS
# =========================================================

class EvenementForm(forms.ModelForm):

    class Meta:
        model = Evenement

        fields = (
            "titre",
            "description",
            "affiche",
            "lieu",
            "adresse",
            "ville",
            "pays",
            "date_evenement",
            "prix",
            "devise",
            "nombre_places",
        )

        widgets = {
            "titre": forms.TextInput(
                attrs={
                    "placeholder": "Nom de l’événement",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Présente ton événement",
                }
            ),
            "affiche": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "lieu": forms.TextInput(
                attrs={
                    "placeholder": "Exemple : Palais de la Culture",
                }
            ),
            "adresse": forms.TextInput(
                attrs={
                    "placeholder": "Adresse complète",
                }
            ),
            "ville": forms.TextInput(
                attrs={
                    "placeholder": "Ville",
                }
            ),
            "date_evenement": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "prix": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "nombre_places": forms.NumberInput(
                attrs={
                    "min": "1",
                    "max": "100",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "date_evenement"
        ].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

    def clean_date_evenement(self):
        date = self.cleaned_data["date_evenement"]

        if date <= timezone.now():
            raise forms.ValidationError(
                "La date de l’événement doit être dans le futur."
            )

        return date

    def clean_prix(self):
        prix = self.cleaned_data["prix"]

        if prix <= Decimal("0"):
            raise forms.ValidationError(
                "Le prix du billet doit être supérieur à zéro."
            )

        return prix

    def clean_nombre_places(self):
        nombre_places = self.cleaned_data["nombre_places"]

        if nombre_places < 1:
            raise forms.ValidationError(
                "L’événement doit avoir au moins une place."
            )

        if nombre_places > 100:
            raise forms.ValidationError(
                (
                    "AfroFans autorise un maximum de "
                    "100 billets par événement."
                ),
            )

        if (
            self.instance.pk
            and nombre_places < self.instance.places_vendues
        ):
            raise forms.ValidationError(
                (
                    "Le nombre de places ne peut pas être "
                    "inférieur au nombre de billets déjà vendus."
                ),
            )

        return nombre_places

    def clean_affiche(self):
        return valider_image(
            self.cleaned_data.get("affiche"),
            "L’affiche",
        )


# =========================================================
# FRAIS DE CRÉATION D’ÉVÉNEMENT
# =========================================================
class PaiementFraisEvenementForm(forms.ModelForm):

    accepter_conditions = forms.BooleanField(
        required=True,
        label=(
            "Je confirme les informations de l’événement "
            "et j’accepte les frais de billetterie HexaQuébec."
        ),
        error_messages={
            "required": (
                "Tu dois accepter les conditions "
                "avant de continuer."
            ),
        },
    )

    class Meta:
        model = PaiementFraisEvenement

        fields = (
            "devise_paiement",
        )

        labels = {
            "devise_paiement": "Devise de paiement",
        }

        widgets = {
            "devise_paiement": forms.Select(
                attrs={
                    "class": "payment-currency-select",
                }
            ),
        }

    def clean_devise_paiement(self):
        devise = self.cleaned_data[
            "devise_paiement"
        ]

        devises_autorisees = (
            "XOF",
            "CAD",
            "EUR",
        )

        if devise not in devises_autorisees:
            raise forms.ValidationError(
                (
                    "Sélectionne une devise autorisée : "
                    "FCFA, dollar canadien ou euro."
                )
            )

        return devise
# =========================================================
# ACHAT DE BILLETS
# =========================================================



# =========================================================
# DEMANDES DE PUBLICATION
# =========================================================

class DemandePublicationForm(forms.ModelForm):

    class Meta:
        model = DemandePublication

        fields = (
            "fichier",
            "miniature",
            "titre",
            "description",
            "categorie",
            "hashtags",
            "message_equipe",
        )

        widgets = {
            "fichier": forms.ClearableFileInput(
                attrs={
                    "accept": "video/mp4,video/webm,video/quicktime",
                }
            ),
            "miniature": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "titre": forms.TextInput(
                attrs={
                    "placeholder": "Titre de la publication",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Description de la vidéo",
                }
            ),
            "hashtags": forms.TextInput(
                attrs={
                    "placeholder": "#musique #talent #afrique",
                }
            ),
            "message_equipe": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": (
                        "Message privé à l’équipe AfroFans"
                    ),
                }
            ),
        }

    def clean_fichier(self):
        fichier = self.cleaned_data.get("fichier")

        if not fichier:
            return fichier

        if not fichier.name.lower().endswith(
            (".mp4", ".webm", ".mov")
        ):
            raise forms.ValidationError(
                "Formats acceptés : MP4, WebM ou MOV."
            )

        if fichier.size > TAILLE_VIDEO_MAXIMALE:
            raise forms.ValidationError(
                "La vidéo ne doit pas dépasser 200 Mo."
            )

        return fichier

    def clean_miniature(self):
        return valider_image(
            self.cleaned_data.get("miniature"),
            "La miniature",
        )


# =========================================================
# CONTRÔLE ET SCANNER DES BILLETS
# =========================================================

class CodeControleEvenementForm(forms.Form):

    code_secret = forms.CharField(
        label="Code secret de contrôle",
        min_length=6,
        max_length=30,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Minimum 6 caractères",
                "autocomplete": "new-password",
            }
        ),
    )

    confirmation = forms.CharField(
        label="Confirmer le code",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirme le code secret",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        code_secret = cleaned_data.get("code_secret")
        confirmation = cleaned_data.get("confirmation")

        if (
            code_secret
            and confirmation
            and code_secret != confirmation
        ):
            self.add_error(
                "confirmation",
                "Les deux codes ne correspondent pas.",
            )

        if code_secret and code_secret.isdigit():
            self.add_error(
                "code_secret",
                (
                    "Utilise des lettres et des chiffres "
                    "pour renforcer la sécurité."
                ),
            )

        return cleaned_data


class OuvrirScannerForm(forms.Form):

    code_secret = forms.CharField(
        label="Code secret du créateur",
        min_length=6,
        max_length=30,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Entre ton code secret",
                "autocomplete": "current-password",
            }
        ),
    )



class AchatTelechargementVideoForm(
    forms.ModelForm
):

    class Meta:
        model = AchatTelechargementVideo

        fields = (
            "devise",
            "methode_paiement",
        )

        labels = {
            "devise": "Tarif de téléchargement",
            "methode_paiement": (
                "Méthode de paiement"
            ),
        }

        widgets = {
            "devise": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "methode_paiement": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["devise"].choices = [
            ("XOF", "50 FCFA"),
            ("CAD", "1 $ CAD"),
            ("EUR", "1 €"),
        ]





# Afrons/forms.py

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from django import forms
from django.core.exceptions import ValidationError

from .models import Profil


MAX_FICHIER = 5 * 1024 * 1024


def valider_fichier(fichier, pdf_autorise=True):

    if fichier.size > MAX_FICHIER:
        raise ValidationError(
            "Le fichier ne doit pas dépasser 5 Mo."
        )

    extension = Path(fichier.name).suffix.lower()

    extensions = {".jpg", ".jpeg", ".png"}

    if pdf_autorise:
        extensions.add(".pdf")

    if extension not in extensions:
        raise ValidationError(
            "Format non autorisé."
        )

    try:
        fichier.seek(0)

        signature = fichier.read(8)
        fichier.seek(0)

        if extension == ".pdf":
            if not signature.startswith(b"%PDF-"):
                raise ValidationError(
                    "Le document PDF est invalide."
                )
        else:
            with Image.open(fichier) as image:
                image.verify()

            fichier.seek(0)

            with Image.open(fichier) as image:
                format_image = image.format

            formats = {
                ".jpg": "JPEG",
                ".jpeg": "JPEG",
                ".png": "PNG",
            }

            if format_image != formats[extension]:
                raise ValidationError(
                    "Le format de l'image est invalide."
                )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        raise ValidationError(
            "Le fichier est endommagé ou invalide."
        )

    finally:
        fichier.seek(0)

    return fichier


class FormulaireVerificationTalent(forms.Form):

    CATEGORIES = [
        ("musique", "Musique"),
        ("humour", "Humour / Comédie"),
        ("danse", "Danse"),
        ("cinema", "Cinéma / Audiovisuel"),
        ("sport", "Sport"),
        ("mode", "Mode"),
        ("creation", "Créateur de contenu"),
        ("art", "Arts et culture"),
        ("autre", "Autre domaine"),
    ]

    TYPES_PIECES = [
        ("passeport", "Passeport"),
        ("carte_identite", "Carte nationale d'identité"),
        ("permis", "Permis de conduire"),
    ]

    prenom = forms.CharField(max_length=150)

    nom = forms.CharField(max_length=150)

    nom_scene = forms.CharField(max_length=150)

    date_naissance = forms.DateField(
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    pays = forms.ChoiceField(
        choices=Profil.PAYS_AUTORISES
    )

    email = forms.EmailField()

    telephone = forms.CharField(max_length=20)

    categorie = forms.ChoiceField(
        choices=CATEGORIES
    )

    lien_public = forms.URLField(
        required=False
    )

    description = forms.CharField(
        widget=forms.Textarea,
        max_length=5000,
    )

    type_piece = forms.ChoiceField(
        choices=TYPES_PIECES
    )

    piece_recto = forms.FileField()

    piece_verso = forms.FileField(
        required=False
    )

    photo_identite = forms.FileField()

    declaration = forms.BooleanField(
        required=True
    )

    def clean_piece_recto(self):
        return valider_fichier(
            self.cleaned_data["piece_recto"]
        )

    def clean_piece_verso(self):

        fichier = self.cleaned_data.get(
            "piece_verso"
        )

        if fichier:
            return valider_fichier(fichier)

        return None

    def clean_photo_identite(self):

        return valider_fichier(
            self.cleaned_data["photo_identite"],
            pdf_autorise=False,
        )

    def clean(self):

        donnees = super().clean()

        type_piece = donnees.get("type_piece")

        verso = donnees.get("piece_verso")

        if (
            type_piece in ("carte_identite", "permis")
            and not verso
        ):
            self.add_error(
                "piece_verso",
                "Le verso est obligatoire pour ce document."
            )

        return donnees