
from django.contrib import admin
from django.utils import timezone

from .models_billetterie import (
    HabilitationBilletterie,
    CodeAccesEvenement,
    ControleurEvenement,
    InvitationControleur,
    ReservationExpiration,
    BilletAcces,
    HistoriqueScan,
)


@admin.register(HabilitationBilletterie)
class HabilitationBilletterieAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "type_vendeur",
        "statut",
        "verifie_le",
    )

    list_filter = (
        "type_vendeur",
        "statut",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    actions = ["approuver_vendeurs"]

    @admin.action(
        description="Approuver les vendeurs sélectionnés"
    )
    def approuver_vendeurs(self, request, queryset):
        queryset.update(
            statut="verifie",
            verifie_le=timezone.now(),
        )


@admin.register(CodeAccesEvenement)
class CodeAccesEvenementAdmin(admin.ModelAdmin):

    list_display = (
        "evenement",
        "cree_le",
    )

    readonly_fields = (
        "cree_le",
    )

    # Le code secret n'est pas affiché
    # dans la liste de l'administration.


@admin.register(ControleurEvenement)
class ControleurEvenementAdmin(admin.ModelAdmin):

    list_display = (
        "prenom",
        "nom",
        "email",
        "pays",
        "evenement",
        "actif",
    )

    list_filter = (
        "actif",
    )

    search_fields = (
        "prenom",
        "nom",
        "email",
    )


@admin.register(InvitationControleur)
class InvitationControleurAdmin(admin.ModelAdmin):

    list_display = (
        "controleur",
        "expire_le",
        "utilise_le",
    )

    readonly_fields = (
        "empreinte_jeton",
        "cree_le",
    )


@admin.register(ReservationExpiration)
class ReservationExpirationAdmin(admin.ModelAdmin):

    list_display = (
        "billet",
        "expire_le",
    )


@admin.register(BilletAcces)
class BilletAccesAdmin(admin.ModelAdmin):

    list_display = (
        "nom_affiche",
        "evenement",
        "statut",
        "utilise_le",
    )

    list_filter = (
        "statut",
        "evenement",
    )

    search_fields = (
        "prenom_participant",
        "nom_participant",
    )


@admin.register(HistoriqueScan)
class HistoriqueScanAdmin(admin.ModelAdmin):

    list_display = (
        "billet",
        "controleur",
        "resultat",
        "scanne_le",
    )

    list_filter = (
        "resultat",
    )
