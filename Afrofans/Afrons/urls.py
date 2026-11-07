from django.urls import path

from . import views_billetterie_stripe

from . import views

from django.urls import path

from . import views_billetterie as vues
from . import views_paiement_afrofans
from . import views_notifications_afrofans
from . import views_publication_afrofans
app_name = "Afrons"


urlpatterns = [

    path(
        "",
        views.flux,
        name="flux",
    ),

    path(
        "explorer/",
        views.explorer,
        name="explorer",
    ),

    path(
        "inscription/",
        views.inscription,
        name="inscription",
    ),

    path(
        "connexion/",
        views.connexion,
        name="connexion",
    ),

    path(
        "deconnexion/",
        views.deconnexion,
        name="deconnexion",
    ),

    path(
        "publier/",
        views.publier_video,
        name="publier_video",
    ),

    path(
        "video/<int:video_id>/",
        views.detail_video,
        name="detail_video",
    ),

    path(
        "video/<int:video_id>/aimer/",
        views.aimer_video,
        name="aimer_video",
    ),

    path(
        "video/<int:video_id>/favori/",
        views.ajouter_favori,
        name="ajouter_favori",
    ),

    path(
        "video/<int:video_id>/commenter/",
        views.commenter_video,
        name="commenter_video",
    ),

    path(
    "video/<int:video_id>/acheter-telechargement/",
    views.acheter_telechargement_video,
    name="acheter_telechargement_video",
    ),

    path(
        "video/<int:video_id>/signaler/",
        views.signaler_video,
        name="signaler_video",
    ),

    path(
        "profil/modifier/",
        views.modifier_profil,
        name="modifier_profil",
    ),

    path(
        "@<str:username>/",
        views.profil_public,
        name="profil_public",
    ),

    path(
        "@<str:username>/suivre/",
        views.suivre_createur,
        name="suivre_createur",
    ),

    path(
    "@<str:username>/abonnes/",
    views.liste_abonnes,
    name="liste_abonnes",
    ),

    path(
    "@<str:username>/abonnements/",
    views.liste_abonnements,
    name="liste_abonnements",
    ),

    path(
    "@<str:username>/don/",
    views.envoyer_don,
    name="envoyer_don",
    ),

    path(
    "dons/<uuid:reference>/confirmation/",
    views.confirmation_don,
    name="confirmation_don",
    ),


    path(
    "billets/<uuid:code_billet>/confirmation/",
    views.confirmation_billet,
    name="confirmation_billet",
    ),

    path(
    "publications/demande/",
    views.demande_publication,
    name="demande_publication",
    ),

    path(
    "publications/mes-demandes/",
    views.mes_demandes_publication,
    name="mes_demandes_publication",
    ),


path(
    "mes-billets/",
    views.mes_tickets,
    name="mes_tickets",
),

path(
    "billets/<str:code_billet>/confirmation/",
    views.confirmation_billet,
    name="confirmation_billet",
),

path(
    "video/<int:video_id>/acheter-telechargement/",
    views.acheter_telechargement_video,
    name="acheter_telechargement_video",
),
path(
    "createur/<str:username>/suivre/",
    views.suivre_createur,
    name="suivre_createur",
),
path(
    "abonnement/<str:username>/",
    views.basculer_abonnement,
    name="basculer_abonnement",
),

path(
    "compte/demander-retrait/",
    views.demander_retrait,
    name="demander_retrait",
),

path(
    "compte/devenir-talent/",
    views.devenir_talent,
    name="devenir_talent",
),

path(
    "compte/action/",
    views.action_compte,
    name="action_compte",
),


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

    


path(
    "evenements/paiement-frais/<int:paiement_id>/",
    views.payer_frais_evenement,
    name="payer_frais_evenement",
),
path(
    "webhooks/stripe/frais-afrofans/",
    views_paiement_afrofans.webhook_stripe_frais_afrofans,
    name="webhook_stripe_frais_afrofans",
),

path(
    "notifications-officielles/<int:notification_id>/ouvrir/",
    views_notifications_afrofans.lire_notification_officielle,
    name="lire_notification_officielle",
),

path(
    "evenements/<int:evenement_id>/valider-publier/",
    views_publication_afrofans.valider_et_publier_evenement,
    name="valider_et_publier_evenement",
),

path(
    "talent/verification/",
    views.formulaire_verification_talent,
    name="formulaire_verification_talent",
),


path(
    "verification-talent/<uuid:identifiant>/payer/",
    views.payer_verification_talent,
    name="payer_verification_talent",
),


path(
    "api/videos/<int:video_id>/commentaires/",
    views.commentaires_video_ajax,
    name="commentaires_video_ajax",
),

path(
    "api/videos/<int:video_id>/commentaires/publier/",
    views.publier_commentaire_ajax,
    name="publier_commentaire_ajax",
),

path(
    "api/commentaires/<int:commentaire_id>/aimer/",
    views.aimer_commentaire_ajax,
    name="aimer_commentaire_ajax",
),

path(
    "api/commentaires/<int:commentaire_id>/supprimer/",
    views.supprimer_commentaire_ajax,
    name="supprimer_commentaire_ajax",
),

path(
    "api/commentaires/<int:commentaire_id>/signaler/",
    views.signaler_commentaire_ajax,
    name="signaler_commentaire_ajax",
),

path(
    "profil/<str:username>/",
    views.profil_public,
    name="profil_public"
),

path(
    "presences/",
    views.presences,
    name="presences"
),

path(
    "presence/demarrer/",
    views.demarrer_presence,
    name="demarrer_presence"
),

path(
    "presence/<int:presence_id>/",
    views.presence_detail,
    name="presence_detail"
),

path(
    "presence/<int:presence_id>/etat/",
    views.presence_etat,
    name="presence_etat"
),

path(
    "presence/<int:presence_id>/heartbeat/",
    views.presence_heartbeat,
    name="presence_heartbeat"
),

path(
    "presence/<int:presence_id>/interaction/",
    views.presence_interaction,
    name="presence_interaction"
),

path(
    "presence/<int:presence_id>/terminer/",
    views.terminer_presence,
    name="terminer_presence"
),
path(
    "presence/<int:presence_id>/livekit-token/",
    views.presence_livekit_token,
    name="presence_livekit_token"
),
path(
    "video/<int:video_id>/supprimer/",
    views.supprimer_video,
    name="supprimer_video",
),

path(
    "video/<int:video_id>/partager/",
    views.enregistrer_partage_video,
    name="enregistrer_partage_video",
),


path(
    "billetterie/<str:code_billet>/checkout/",
    views_billetterie_stripe.checkout_billet_afrofans,
    name="checkout_billet_afrofans",
),

path(
    "stripe/webhook/billets/",
    views_billetterie_stripe.webhook_billet_afrofans,
    name="webhook_billet_afrofans",
),


# ============================================================
# AFROFANS — ACHAT ET TÉLÉCHARGEMENT VIDÉO
# ============================================================

path(
    "video/<int:video_id>/acheter-telechargement/",
    views.acheter_telechargement_video,
    name="acheter_telechargement_video",
),

path(
    "video/achat/<int:achat_id>/confirmation/",
    views.confirmation_telechargement_video,
    name="confirmation_telechargement_video",
),

path(
    "video/achat/<int:achat_id>/telecharger/",
    views.telecharger_video_payee,
    name="telecharger_video_payee",
),


path(
    "stripe/webhook/videos/",
    views.webhook_telechargement_video,
    name="webhook_telechargement_video",
),
path(
    "parametres/compte-retrait/",
    views.configurer_compte_retrait,
    name="configurer_compte_retrait",
),

]