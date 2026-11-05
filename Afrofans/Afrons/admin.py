from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import (
    Abonnement,
  
    Commentaire,
    ControleEvenement,
    ControleTicket,
    DemandePublication,
    Don,
    Evenement,
    Favori,
    Jaime,
    NotificationEvenement,
    PaiementFraisEvenement,
    Profil,
    Signalement,
    TicketEntree,
    Video,
)
from .models import Musique


from .models import AchatTelechargementVideo


from . import admin_billetterie






from .services_notifications import (
    notifier_publication_evenement,
)


# =========================================================
# IDENTITÉ DE L’ADMINISTRATION
# =========================================================

admin.site.site_header = "Administration AfroFans"
admin.site.site_title = "AfroFans Admin"
admin.site.index_title = (
    "Gestion de la plateforme AfroFans par HexaQuébec"
)


# =========================================================
# PROFILS
# =========================================================

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):

    list_display = (
        "utilisateur",
        "nom_scene",
        "type_compte",
        "pays",
        "ville",
        "est_certifie",
        "cree_le",
    )

    list_filter = (
        "type_compte",
        "est_certifie",
        "pays",
        "cree_le",
    )

    search_fields = (
        "utilisateur__username",
        "utilisateur__email",
        "utilisateur__first_name",
        "utilisateur__last_name",
        "nom_scene",
        "numero_telephone",
        "ville",
    )

    list_editable = (
        "est_certifie",
    )

    readonly_fields = (
        "cree_le",
    )

    autocomplete_fields = (
        "utilisateur",
    )

    list_select_related = (
        "utilisateur",
    )

    ordering = (
        "-cree_le",
    )

    list_per_page = 30


# =========================================================
# VIDÉOS
# =========================================================

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "auteur",
        "categorie",
        "vues",
        "est_publiee",
        "est_a_la_une",
        "creee_le",
    )

    list_filter = (
        "categorie",
        "est_publiee",
        "est_a_la_une",
        "creee_le",
    )

    search_fields = (
        "titre",
        "auteur__username",
        "auteur__email",
        "description",
        "hashtags",
    )

    list_editable = (
        "est_publiee",
        "est_a_la_une",
    )

    autocomplete_fields = (
        "auteur",
    )

    readonly_fields = (
        "vues",
        "creee_le",
    )

    date_hierarchy = "creee_le"

    ordering = (
        "-creee_le",
    )

    list_per_page = 30


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):

    list_display = (
        "utilisateur",
        "video",
        "contenu",
        "est_visible",
        "cree_le",
    )

    list_filter = (
        "est_visible",
        "cree_le",
    )

    search_fields = (
        "utilisateur__username",
        "contenu",
        "video__titre",
    )

    list_editable = (
        "est_visible",
    )

    autocomplete_fields = (
        "utilisateur",
        "video",
    )

    readonly_fields = (
        "cree_le",
    )

    ordering = (
        "-cree_le",
    )


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):

    list_display = (
        "video",
        "auteur",
        "raison",
        "traite",
        "cree_le",
    )

    list_filter = (
        "raison",
        "traite",
        "cree_le",
    )

    search_fields = (
        "video__titre",
        "auteur__username",
        "details",
    )

    list_editable = (
        "traite",
    )

    autocomplete_fields = (
        "video",
        "auteur",
    )

    readonly_fields = (
        "cree_le",
    )

    ordering = (
        "-cree_le",
    )


# =========================================================
# INTERACTIONS
# =========================================================

@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):

    list_display = (
        "fan",
        "createur",
        "cree_le",
    )

    search_fields = (
        "fan__username",
        "createur__username",
    )

    autocomplete_fields = (
        "fan",
        "createur",
    )

    ordering = (
        "-cree_le",
    )


@admin.register(Jaime)
class JaimeAdmin(admin.ModelAdmin):

    list_display = (
        "utilisateur",
        "video",
        "cree_le",
    )

    search_fields = (
        "utilisateur__username",
        "video__titre",
    )

    autocomplete_fields = (
        "utilisateur",
        "video",
    )

    ordering = (
        "-cree_le",
    )


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):

    list_display = (
        "utilisateur",
        "video",
        "cree_le",
    )

    search_fields = (
        "utilisateur__username",
        "video__titre",
    )

    autocomplete_fields = (
        "utilisateur",
        "video",
    )

    ordering = (
        "-cree_le",
    )


# =========================================================
# DONS
# =========================================================

@admin.register(Don)
class DonAdmin(admin.ModelAdmin):

    list_display = (
        "reference",
        "donateur",
        "createur",
        "montant",
        "devise",
        "methode_paiement",
        "statut",
        "cree_le",
    )

    list_filter = (
        "statut",
        "devise",
        "methode_paiement",
        "cree_le",
    )

    search_fields = (
        "reference",
        "donateur__username",
        "donateur__email",
        "createur__username",
        "createur__email",
        "message",
    )

    readonly_fields = (
        "reference",
        "cree_le",
        "modifie_le",
    )

    autocomplete_fields = (
        "donateur",
        "createur",
    )

    ordering = (
        "-cree_le",
    )

    list_per_page = 30


# =========================================================
# FRAIS D’ÉVÉNEMENT
# =========================================================

class PaiementFraisEvenementInline(
    admin.StackedInline
):
    model = PaiementFraisEvenement

    extra = 0
    can_delete = False
    max_num = 1

    fields = (
        "reference",
        "statut",
        "montant_original_xof",
        "montant_tps_xof",
        "montant_tvq_xof",
        "total_xof",
        "devise_paiement",
        "taux_conversion",
        "total_converti",
        "cree_le",
        "paye_le",
    )

    readonly_fields = (
        "reference",
        "montant_original_xof",
        "montant_tps_xof",
        "montant_tvq_xof",
        "total_xof",
        "total_converti",
        "cree_le",
        "paye_le",
    )


@admin.register(PaiementFraisEvenement)
class PaiementFraisEvenementAdmin(admin.ModelAdmin):

    list_display = (
        "reference",
        "evenement",
        "createur",
        "total_xof",
        "devise_paiement",
        "total_converti",
        "statut",
        "cree_le",
        "paye_le",
    )

    list_filter = (
        "statut",
        "devise_paiement",
        "cree_le",
        "paye_le",
    )

    search_fields = (
        "reference",
        "evenement__titre",
        "createur__username",
        "createur__email",
    )

    readonly_fields = (
        "reference",
        "montant_original_xof",
        "montant_tps_xof",
        "montant_tvq_xof",
        "total_xof",
        "total_converti",
        "cree_le",
        "paye_le",
    )

    autocomplete_fields = (
        "evenement",
        "createur",
    )

    ordering = (
        "-cree_le",
    )

    list_per_page = 30

    actions = (
        "confirmer_comme_payes",
    )

    @admin.action(
        description="Confirmer les paiements sélectionnés",
    )
    def confirmer_comme_payes(
        self,
        request,
        queryset,
    ):
        nombre = 0

        for paiement in queryset.exclude(
            statut="paye"
        ):
            with transaction.atomic():
                paiement.statut = "paye"
                paiement.paye_le = timezone.now()
                paiement.save()

                evenement = paiement.evenement

                evenement.frais_billetterie_payes = True
                evenement.frais_payes_le = paiement.paye_le

                if evenement.statut in (
                    "brouillon",
                    "paiement_attente",
                ):
                    evenement.statut = "en_attente"

                evenement.save(
                    update_fields=[
                        "frais_billetterie_payes",
                        "frais_payes_le",
                        "statut",
                        "modifie_le",
                    ]
                )

                nombre += 1

        self.message_user(
            request,
            f"{nombre} paiement(s) confirmé(s).",
            level=messages.SUCCESS,
        )


# =========================================================
# ÉVÉNEMENTS
# =========================================================

@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "createur",
        "date_evenement",
        "prix_formate",
        "nombre_places",
        "afficher_places_vendues",
        "afficher_places_restantes",
        "afficher_frais_total",
        "afficher_paiement",
        "afficher_notifications",
        "statut",
    )

    list_filter = (
        "statut",
        "frais_billetterie_payes",
        "notifications_envoyees",
        "devise",
        "pays",
        "date_evenement",
        "cree_le",
    )

    search_fields = (
        "titre",
        "description",
        "createur__username",
        "createur__email",
        "createur__profil__nom_scene",
        "lieu",
        "adresse",
        "ville",
        "paiement_frais__reference",
    )

    readonly_fields = (
        "afficher_places_vendues",
        "afficher_places_restantes",
        "afficher_revenu_total",
        "afficher_nombre_tranches",
        "afficher_frais_ht",
        "afficher_tps",
        "afficher_tvq",
        "afficher_frais_total",
        "frais_billetterie_payes",
        "frais_payes_le",
        "notifications_envoyees",
        "cree_le",
        "modifie_le",
    )

    autocomplete_fields = (
        "createur",
    )

    ordering = (
        "-date_evenement",
    )

    list_per_page = 25
    date_hierarchy = "date_evenement"

    inlines = (
        PaiementFraisEvenementInline,
    )

    actions = (
        "confirmer_paiement_frais",
        "publier_evenements",
        "remettre_en_attente",
        "refuser_evenements",
        "annuler_evenements",
    )

    fieldsets = (
        (
            "Créateur et événement",
            {
                "fields": (
                    "createur",
                    "titre",
                    "description",
                    "affiche",
                ),
            },
        ),
        (
            "Lieu",
            {
                "fields": (
                    "lieu",
                    "adresse",
                    "ville",
                    "pays",
                ),
            },
        ),
        (
            "Date et billetterie",
            {
                "fields": (
                    "date_evenement",
                    "prix",
                    "devise",
                    "nombre_places",
                ),
            },
        ),
        (
            "Frais de billetterie HexaQuébec",
            {
                "fields": (
                    "afficher_nombre_tranches",
                    "afficher_frais_ht",
                    "afficher_tps",
                    "afficher_tvq",
                    "afficher_frais_total",
                    "frais_billetterie_payes",
                    "frais_payes_le",
                ),
            },
        ),
        (
            "Statistiques de vente",
            {
                "fields": (
                    "afficher_places_vendues",
                    "afficher_places_restantes",
                    "afficher_revenu_total",
                ),
            },
        ),
        (
            "Validation AfroFans",
            {
                "fields": (
                    "statut",
                    "motif_refus",
                    "notifications_envoyees",
                ),
                "description": (
                    "Confirme d’abord le paiement des frais, "
                    "puis publie l’événement."
                ),
            },
        ),
        (
            "Informations techniques",
            {
                "classes": ("collapse",),
                "fields": (
                    "cree_le",
                    "modifie_le",
                ),
            },
        ),
    )

    @admin.display(
        description="Prix du billet",
        ordering="prix",
    )
    def prix_formate(self, objet):
        return (
            f"{objet.prix:,.2f} "
            f"{objet.devise}"
        )

    @admin.display(
        description="Places vendues",
    )
    def afficher_places_vendues(self, objet):
        return objet.places_vendues

    @admin.display(
        description="Places restantes",
    )
    def afficher_places_restantes(self, objet):
        return objet.places_restantes

    @admin.display(
        description="Revenu des billets",
    )
    def afficher_revenu_total(self, objet):
        return (
            f"{objet.revenu_total:,.2f} "
            f"{objet.devise}"
        )

    @admin.display(
        description="Tranches facturées",
    )
    def afficher_nombre_tranches(self, objet):
        return (
            f"{objet.nombre_tranches} "
            "tranche(s) de 10 billets"
        )

    @admin.display(
        description="Frais hors taxes",
    )
    def afficher_frais_ht(self, objet):
        return (
            f"{objet.frais_billetterie_ht:,.2f} FCFA"
        )

    @admin.display(
        description="TPS — 5 %",
    )
    def afficher_tps(self, objet):
        return (
            f"{objet.montant_tps:,.2f} FCFA"
        )

    @admin.display(
        description="TVQ — 9,975 %",
    )
    def afficher_tvq(self, objet):
        return (
            f"{objet.montant_tvq:,.2f} FCFA"
        )

    @admin.display(
        description="Frais TTC",
    )
    def afficher_frais_total(self, objet):
        return (
            f"{objet.frais_billetterie_ttc:,.2f} FCFA"
        )

    @admin.display(
        description="Paiement",
        boolean=True,
        ordering="frais_billetterie_payes",
    )
    def afficher_paiement(self, objet):
        return objet.frais_billetterie_payes

    @admin.display(
        description="Abonnés notifiés",
        boolean=True,
        ordering="notifications_envoyees",
    )
    def afficher_notifications(self, objet):
        return objet.notifications_envoyees

    @admin.action(
        description="Confirmer le paiement des frais",
    )
    def confirmer_paiement_frais(
        self,
        request,
        queryset,
    ):
        nombre_confirmes = 0
        nombre_sans_paiement = 0

        for evenement in queryset:
            try:
                paiement = evenement.paiement_frais
            except PaiementFraisEvenement.DoesNotExist:
                nombre_sans_paiement += 1
                continue

            with transaction.atomic():
                if paiement.statut != "paye":
                    paiement.statut = "paye"
                    paiement.paye_le = timezone.now()
                    paiement.save()

                evenement.frais_billetterie_payes = True
                evenement.frais_payes_le = paiement.paye_le

                if evenement.statut in (
                    "brouillon",
                    "paiement_attente",
                ):
                    evenement.statut = "en_attente"

                evenement.save(
                    update_fields=[
                        "frais_billetterie_payes",
                        "frais_payes_le",
                        "statut",
                        "modifie_le",
                    ]
                )

            nombre_confirmes += 1

        if nombre_confirmes:
            self.message_user(
                request,
                (
                    f"{nombre_confirmes} paiement(s) "
                    "confirmé(s)."
                ),
                level=messages.SUCCESS,
            )

        if nombre_sans_paiement:
            self.message_user(
                request,
                (
                    f"{nombre_sans_paiement} événement(s) "
                    "sans dossier de paiement."
                ),
                level=messages.WARNING,
            )

    @admin.action(
        description=(
            "Publier les événements payés "
            "et notifier les abonnés"
        ),
    )
    def publier_evenements(
        self,
        request,
        queryset,
    ):
        nombre_publies = 0
        nombre_non_payes = 0
        total_notifications = 0

        for evenement in queryset:
            if not evenement.frais_billetterie_payes:
                nombre_non_payes += 1
                continue

            if evenement.statut == "publie":
                continue

            with transaction.atomic():
                evenement.statut = "publie"
                evenement.motif_refus = ""
                evenement.save(
                    update_fields=[
                        "statut",
                        "motif_refus",
                        "modifie_le",
                    ]
                )

            total_notifications += (
                notifier_publication_evenement(
                    evenement
                )
            )

            nombre_publies += 1

        if nombre_publies:
            self.message_user(
                request,
                (
                    f"{nombre_publies} événement(s) publié(s). "
                    f"{total_notifications} notification(s) "
                    "créée(s)."
                ),
                level=messages.SUCCESS,
            )

        if nombre_non_payes:
            self.message_user(
                request,
                (
                    f"{nombre_non_payes} événement(s) non "
                    "publié(s), car les frais ne sont pas payés."
                ),
                level=messages.ERROR,
            )

    @admin.action(
        description="Remettre en attente de validation",
    )
    def remettre_en_attente(
        self,
        request,
        queryset,
    ):
        nombre = queryset.update(
            statut="en_attente"
        )

        self.message_user(
            request,
            f"{nombre} événement(s) remis en attente.",
            level=messages.SUCCESS,
        )

    @admin.action(
        description="Refuser les événements sélectionnés",
    )
    def refuser_evenements(
        self,
        request,
        queryset,
    ):
        nombre = queryset.update(
            statut="refuse"
        )

        self.message_user(
            request,
            f"{nombre} événement(s) refusé(s).",
            level=messages.WARNING,
        )

    @admin.action(
        description="Annuler les événements sélectionnés",
    )
    def annuler_evenements(
        self,
        request,
        queryset,
    ):
        nombre = queryset.update(
            statut="annule"
        )

        self.message_user(
            request,
            f"{nombre} événement(s) annulé(s).",
            level=messages.WARNING,
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "createur",
                "createur__profil",
                "paiement_frais",
            )
        )




# =========================================================
# TICKETS INDIVIDUELS
# =========================================================

@admin.register(TicketEntree)
class TicketEntreeAdmin(admin.ModelAdmin):

    list_display = (
        "code_public",
        "evenement",
        "proprietaire",
        "numero",
        "statut",
        "utilise_le",
    )

    list_filter = (
        "statut",
        "evenement",
    )

    search_fields = (
        "code_public",
        "nom_participant",
        "proprietaire__username",
        "evenement__titre",
    )

    readonly_fields = (
        "identifiant",
        "code_public",
        "cree_le",
        "utilise_le",
        "controle_par",
    )

    autocomplete_fields = (
        "evenement",
        "proprietaire",
    )

    ordering = (
        "-cree_le",
    )

    list_per_page = 40


@admin.register(ControleEvenement)
class ControleEvenementAdmin(admin.ModelAdmin):

    list_display = (
        "evenement",
        "modifie_le",
    )

    search_fields = (
        "evenement__titre",
        "evenement__createur__username",
    )

    autocomplete_fields = (
        "evenement",
    )

    readonly_fields = (
        "code_secret_hash",
        "modifie_le",
    )


@admin.register(ControleTicket)
class ControleTicketAdmin(admin.ModelAdmin):

    list_display = (
        "evenement",
        "ticket",
        "controleur",
        "resultat",
        "controle_le",
    )

    list_filter = (
        "resultat",
        "evenement",
        "controle_le",
    )

    search_fields = (
        "ticket__code_public",
        "evenement__titre",
        "controleur__username",
        "code_recu",
    )

    readonly_fields = (
        "evenement",
        "ticket",
        "controleur",
        "code_recu",
        "resultat",
        "controle_le",
    )

    ordering = (
        "-controle_le",
    )


# =========================================================
# DEMANDES DE PUBLICATION
# =========================================================

@admin.register(DemandePublication)
class DemandePublicationAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "demandeur",
        "categorie",
        "statut",
        "video_publiee",
        "cree_le",
    )

    list_filter = (
        "statut",
        "categorie",
        "cree_le",
    )

    search_fields = (
        "titre",
        "demandeur__username",
        "demandeur__email",
        "hashtags",
        "message_equipe",
    )

    readonly_fields = (
        "cree_le",
        "modifie_le",
    )

    autocomplete_fields = (
        "demandeur",
        "video_publiee",
    )

    ordering = (
        "-cree_le",
    )


# =========================================================
# NOTIFICATIONS D’ÉVÉNEMENT
# =========================================================

@admin.register(NotificationEvenement)
class NotificationEvenementAdmin(admin.ModelAdmin):

    list_display = (
        "destinataire",
        "evenement",
        "titre",
        "est_lue",
        "cree_le",
    )

    list_filter = (
        "est_lue",
        "cree_le",
        "evenement",
    )

    search_fields = (
        "destinataire__username",
        "destinataire__email",
        "evenement__titre",
        "titre",
        "message",
    )

    readonly_fields = (
        "cree_le",
    )

    autocomplete_fields = (
        "destinataire",
        "evenement",
    )

    ordering = (
        "-cree_le",
    )

    list_per_page = 40




@admin.register(Musique)
class MusiqueAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "artiste",
        "genre",
        "est_autorisee",
        "est_active",
        "est_populaire",
        "nombre_utilisations",
        "cree_le",
    )

    list_filter = (
        "genre",
        "est_autorisee",
        "est_active",
        "est_populaire",
    )

    search_fields = (
        "titre",
        "artiste",
    )

    list_editable = (
        "est_autorisee",
        "est_active",
        "est_populaire",
    )

    readonly_fields = (
        "nombre_utilisations",
        "cree_le",
        "modifie_le",
    )

    ordering = (
        "-est_populaire",
        "-nombre_utilisations",
        "titre",
    )




@admin.register(AchatTelechargementVideo)
class AchatTelechargementVideoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "reference",
        "video",
        "acheteur",
        "montant_total",
        "devise",
        "commission_afrofans",
        "montant_createur",
        "methode_paiement",
        "statut",
        "nombre_telechargements",
        "cree_le",
    )

    list_filter = (
        "statut",
        "devise",
        "methode_paiement",
        "cree_le",
    )

    search_fields = (
        "reference",
        "reference_paiement",
        "video__titre",
        "acheteur__username",
        "acheteur__email",
        "video__auteur__username",
    )

    list_editable = (
        "statut",
    )

    readonly_fields = (
        "reference",
        "montant_total",
        "commission_afrofans",
        "montant_createur",
        "nombre_telechargements",
        "dernier_telechargement",
        "cree_le",
        "paye_le",
    )

    autocomplete_fields = (
        "acheteur",
        "video",
    )

    ordering = (
        "-cree_le",
    )





# ============================================================
# AFROFANS — ADMINISTRATION DES MODÈLES COMPLÉMENTAIRES
# Entreprise : HexaQuébec
# ============================================================

from django.apps import apps
from django.contrib import admin


# ============================================================
# 1. MODÈLES À AJOUTER
# ============================================================

MODELES_AFROFANS = {

    # COMMENTAIRES
    "JaimeCommentaire": {
        "colonnes": (
            "utilisateur",
            "commentaire",
            "cree_le",
        ),
        "filtres": ("cree_le",),
    },

    "SignalementCommentaire": {
        "colonnes": (
            "commentaire",
            "motif",
            "traite",
            "cree_le",
        ),
        "filtres": (
            "motif",
            "traite",
            "cree_le",
        ),
    },

    # BILLETTERIE
    "BilletEvenement": {
        "colonnes": (
            "evenement",
            "quantite",
            "montant_total",
            "statut",
        ),
        "filtres": ("statut",),
        "prive": True,
    },

    # VÉRIFICATION DES TALENTS
    "DemandeVerificationTalent": {
        "colonnes": (
            "identifiant",
            "nom_artistique",
            "statut",
            "date_soumission",
        ),
        "filtres": ("statut",),
        "prive": True,
    },

    # PRÉSENCE EN TEMPS RÉEL
    "PresenceAfroFans": {
        "colonnes": (
            "sujet",
            "est_active",
            "cree_le",
        ),
        "filtres": (
            "est_active",
            "cree_le",
        ),
    },

    "PresenceSpectateur": {
        "colonnes": (
            "id",
            "derniere_activite",
        ),
        "filtres": ("derniere_activite",),
    },

    "PresenceMessage": {
        "colonnes": (
            "id",
            "type_message",
            "cree_le",
        ),
        "filtres": ("type_message",),
    },

    "PresenceJaime": {
        "colonnes": ("id", "cree_le"),
        "filtres": ("cree_le",),
    },

    # PAIEMENTS STRIPE
    "PaiementBilletStripe": {
        "colonnes": (
            "reservation",
            "montant_centimes",
            "devise",
            "statut",
            "cree_le",
        ),
        "filtres": (
            "statut",
            "devise",
            "cree_le",
        ),
        "prive": True,
    },

    # COMMISSIONS AFROFANS
    "LotCommissionAfroFans": {
        "colonnes": (
            "numero_lot",
            "nombre_billets",
            "commission_centimes",
            "devise",
        ),
        "filtres": ("devise",),
        "prive": True,
    },

    "BilletUnitePayeeAfroFans": {
        "colonnes": (
            "numero_unite",
            "montant_centimes",
            "devise",
        ),
        "filtres": ("devise",),
        "prive": True,
    },
}


# ============================================================
# 2. ADMINISTRATION SÉCURISÉE
# ============================================================

class AfroFansComplementAdmin(admin.ModelAdmin):

    list_per_page = 30
    show_full_result_count = False
    actions = None

    # Consultation uniquement pour les nouveaux modèles.

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):

        if getattr(self, "modele_prive", False):
            return (
                request.user.is_active
                and request.user.is_superuser
            )

        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):

        if getattr(self, "modele_prive", False):
            return (
                request.user.is_active
                and request.user.is_superuser
            )

        return super().has_view_permission(request, obj)

    def get_fields(self, request, obj=None):

        # N'afficher que les colonnes autorisées.
        # Évite les documents d'identité et secrets Stripe.

        return list(self.list_display)

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)


# ============================================================
# 3. ENREGISTREMENT AUTOMATIQUE
# ============================================================

application = apps.get_app_config("Afrons")

for nom_modele, configuration in MODELES_AFROFANS.items():

    modele = application.get_model(nom_modele)

    # Éviter les doublons.
    if admin.site.is_registered(modele):
        continue

    champs_existants = {
        champ.name
        for champ in modele._meta.fields
    }

    colonnes = tuple(
        champ
        for champ in configuration["colonnes"]
        if champ in champs_existants
    )

    filtres = tuple(
        champ
        for champ in configuration["filtres"]
        if champ in champs_existants
    )

    classe_admin = type(
        f"{nom_modele}Admin",
        (AfroFansComplementAdmin,),
        {
            "list_display": colonnes or ("__str__",),
            "list_filter": filtres,
            "modele_prive": configuration.get(
                "prive",
                False,
            ),
            "__module__": __name__,
        },
    )

    admin.site.register(
        modele,
        classe_admin,
    )


# ============================================================
# 4. IDENTITÉ ADMIN AFROFANS
# ============================================================

admin.site.site_header = (
    "AfroFans | Administration"
)

admin.site.site_title = (
    "AfroFans — HexaQuébec"
)

admin.site.index_title = (
    "Gestion de la plateforme AfroFans"
)

# ============================================================
# FIN
# ============================================================
