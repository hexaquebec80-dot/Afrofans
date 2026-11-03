
from django.urls import path

from . import views_billetterie as vues


urlpatterns = [

    # Événements
    path(
        "evenements/creer/",
        vues.creer_evenement,
        name="creer_evenement",
    ),

    path(
        "evenements/<int:evenement_id>/modifier/",
        vues.modifier_evenement,
        name="modifier_evenement",
    ),

    path(
        "evenements/<int:evenement_id>/",
        vues.detail_evenement,
        name="detail_evenement",
    ),

    # Achats
    path(
        "evenements/<int:evenement_id>/acheter/",
        vues.acheter_billet,
        name="acheter_billet",
    ),

    path(
        "billets/<str:code_billet>/confirmation/",
        vues.confirmation_billet,
        name="confirmation_billet",
    ),

    # Gestion des événements
    path(
        "evenements/<int:evenement_id>/ouvrir/",
        vues.ouvrir_evenement,
        name="ouvrir_evenement",
    ),

    path(
        "evenements/<int:evenement_id>/terminer/",
        vues.terminer_evenement,
        name="terminer_evenement",
    ),

    path(
        "evenements/<int:evenement_id>/presences/",
        vues.tableau_presence,
        name="tableau_presence",
    ),

    # Contrôleurs
    path(
        "evenements/<int:evenement_id>/controleurs/ajouter/",
        vues.creer_controleur,
        name="creer_controleur",
    ),

    path(
        "controleurs/<uuid:controleur_id>/renvoyer/",
        vues.renvoyer_invitation,
        name="renvoyer_invitation",
    ),

    path(
        "controleurs/<uuid:controleur_id>/desactiver/",
        vues.desactiver_controleur,
        name="desactiver_controleur",
    ),

    path(
        "controleurs/<uuid:controleur_id>/invitation/<str:jeton>/",
        vues.invitation_controleur,
        name="invitation_controleur",
    ),

    path(
        "controleurs/<uuid:controleur_id>/code/",
        vues.code_controleur,
        name="code_controleur",
    ),

    path(
        "controleurs/<uuid:controleur_id>/scanner/",
        vues.scanner_evenement,
        name="scanner_evenement",
    ),

    # Billets individuels
    path(
        "billets/individuels/<uuid:billet_id>/participant/",
        vues.nommer_participant,
        name="nommer_participant",
    ),

    path(
        "billets/individuels/<uuid:billet_id>/qr.png",
        vues.image_qr_billet,
        name="image_qr_billet",
    ),
]
