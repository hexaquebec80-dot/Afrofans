
from decimal import Decimal

from django import forms
from django.utils import timezone

from .models import Evenement, BilletEvenement
from .models_billetterie import ControleurEvenement


# =====================================================
# AFROFANS - PAYS ACCEPTÉS
# =====================================================

CHOIX_PAYS = [
    ("", "Sélectionnez le pays de l'événement"),
    ("CA", "Canada"),
    ("FR", "France"),
    ("ML", "Mali"),
    ("SN", "Sénégal"),
    ("CI", "Côte d'Ivoire"),
]


# =====================================================
# 1. CRÉATION ET MODIFICATION D'ÉVÉNEMENT
# SANS AFFICHE OBLIGATOIRE
# =====================================================

class EvenementForm(forms.ModelForm):

    pays = forms.ChoiceField(
        label="Pays de l'événement",
        choices=CHOIX_PAYS,
        required=True,
        widget=forms.Select(
            attrs={
                "class": "af-form-control",
            }
        ),
        help_text=(
            "Sélectionnez le pays où se déroulera "
            "l'événement. Le pays de paiement "
            "sera choisi à l'étape suivante."
        ),
    )

    date_evenement = forms.DateTimeField(
        label="Date et heure de l'événement",
        required=True,
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "type": "datetime-local",
                "class": "af-form-control",
            },
        ),
    )

    class Meta:

        model = Evenement

        # Le billet est généré en HTML/CSS.
        # Aucune affiche n'est demandée.

        fields = [
            "titre",
            "description",
            "lieu",
            "adresse",
            "ville",
            "pays",
            "date_evenement",
            "prix",
            "devise",
            "nombre_places",
        ]

        labels = {
            "titre": "Nom de l'événement",
            "description": "Description",
            "lieu": "Lieu de l'événement",
            "adresse": "Adresse",
            "ville": "Ville",
            "prix": "Prix d'un billet",
            "devise": "Devise du billet",
            "nombre_places": "Nombre de billets",
        }

        widgets = {

            "titre": forms.TextInput(
                attrs={
                    "placeholder": "Ex. Concert AfroFans",
                    "maxlength": 160,
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Présentez l'événement, "
                        "les artistes et les activités."
                    ),
                }
            ),

            "lieu": forms.TextInput(
                attrs={
                    "placeholder": "Ex. Palais de la Culture",
                }
            ),

            "adresse": forms.TextInput(
                attrs={
                    "placeholder": "Adresse du lieu",
                }
            ),

            "ville": forms.TextInput(
                attrs={
                    "placeholder": "Ex. Montréal, Paris, Bamako",
                }
            ),

            "prix": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Prix du billet",
                }
            ),

            "nombre_places": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 100,
                    "step": 1,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for champ in self.fields.values():

            classes = champ.widget.attrs.get(
                "class", ""
            )

            champ.widget.attrs["class"] = (
                classes + " af-form-control"
            ).strip()

        self.fields["nombre_places"].help_text = (
            "Maximum 100 billets par événement."
        )

        self.fields["description"].help_text = (
            "La description sera visible "
            "sur la page de l'événement."
        )

    # ==========================================
    # PAYS
    # ==========================================

    def clean_pays(self):

        pays = self.cleaned_data["pays"]

        codes_valides = {
            "CA", "FR", "ML", "SN", "CI"
        }

        if pays not in codes_valides:

            raise forms.ValidationError(
                "Veuillez sélectionner un pays valide."
            )

        return pays

    # ==========================================
    # NOMBRE DE PLACES
    # ==========================================

    def clean_nombre_places(self):

        nombre = self.cleaned_data["nombre_places"]

        if not 1 <= nombre <= 100:

            raise forms.ValidationError(
                "Le nombre de billets doit "
                "être compris entre 1 et 100."
            )

        return nombre

    # ==========================================
    # DATE DE L'ÉVÉNEMENT
    # ==========================================

    def clean_date_evenement(self):

        date = self.cleaned_data["date_evenement"]

        if date <= timezone.now():

            raise forms.ValidationError(
                "La date de l'événement "
                "doit être dans le futur."
            )

        return date

    # ==========================================
    # PRIX
    # ==========================================

    def clean_prix(self):

        prix = self.cleaned_data["prix"]

        if prix < Decimal("0.01"):

            raise forms.ValidationError(
                "Le prix doit être supérieur à zéro."
            )

        return prix

    # ==========================================
    # TITRE
    # ==========================================

    def clean_titre(self):

        titre = self.cleaned_data["titre"].strip()

        if len(titre) < 3:

            raise forms.ValidationError(
                "Le titre doit contenir "
                "au moins 3 caractères."
            )

        return titre


# =====================================================
# 2. FORMULAIRE D'ACHAT DES BILLETS
# =====================================================

class AchatBilletForm(forms.ModelForm):

    accept_absence = forms.BooleanField(
        required=True,
        label=(
            "Je comprends qu'une simple absence "
            "à un événement tenu normalement "
            "ne donne pas automatiquement droit "
            "à un remboursement, sous réserve "
            "des lois applicables."
        ),
        widget=forms.CheckboxInput(
            attrs={
                "class": "af-checkbox",
            }
        ),
    )

    class Meta:

        model = BilletEvenement

        fields = [
            "nom_participant",
            "courriel",
            "quantite",
            "methode_paiement",
        ]

        widgets = {

            "nom_participant": forms.TextInput(
                attrs={
                    "placeholder": "Nom complet",
                }
            ),

            "courriel": forms.EmailInput(
                attrs={
                    "placeholder": "exemple@gmail.com",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 100,
                }
            ),
        }

    def __init__(
        self,
        *args,
        evenement=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        if evenement is not None:
            self.instance.evenement = evenement

        self.fields["nom_participant"].label = (
            "Nom du premier participant"
        )

        self.fields["courriel"].label = (
            "Courriel de réception des billets"
        )

        self.fields["quantite"].initial = 1

        # Seul le paiement par carte Stripe
        # est proposé actuellement.
        # Wave / Orange Money restent indisponibles.

        self.fields["methode_paiement"].choices = [
            (
                "carte",
                "Carte bancaire — Stripe"
            ),
        ]

        for champ in self.fields.values():

            classes = champ.widget.attrs.get(
                "class", ""
            )

            champ.widget.attrs["class"] = (
                classes + " af-form-control"
            ).strip()

    def clean_quantite(self):

        quantite = self.cleaned_data["quantite"]

        if not 1 <= quantite <= 100:

            raise forms.ValidationError(
                "Choisissez entre 1 et 100 billets."
            )

        return quantite

    def clean_courriel(self):

        return (
            self.cleaned_data["courriel"]
            .strip()
            .lower()
        )

    def clean_nom_participant(self):

        nom = (
            self.cleaned_data["nom_participant"]
            .strip()
        )

        if len(nom) < 2:

            raise forms.ValidationError(
                "Indiquez un nom valide."
            )

        return nom


# =====================================================
# 3. FORMULAIRE DES CONTRÔLEURS
# =====================================================

class ControleurEvenementForm(forms.ModelForm):

    class Meta:

        model = ControleurEvenement

        fields = [
            "nom",
            "prenom",
            "pays",
            "email",
        ]

        widgets = {

            "nom": forms.TextInput(
                attrs={
                    "placeholder": "Nom",
                }
            ),

            "prenom": forms.TextInput(
                attrs={
                    "placeholder": "Prénom",
                }
            ),

            "pays": forms.TextInput(
                attrs={
                    "placeholder": "Pays du contrôleur",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "controleur@exemple.com",
                }
            ),
        }

    def clean_email(self):

        return (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )
