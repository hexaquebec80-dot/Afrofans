from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.mail import EmailMessage
from .models import Abonnement
from .forms import CommentaireForm
from .forms import InscriptionForm
from .forms import ProfilForm
from .forms import SignalementForm
from .forms import UtilisateurForm
from .forms import VideoForm

from .models import Abonnement, Musique
from .models import Favori
from .models import Jaime
from .models import Signalement
from .models import Video
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST


from .forms import DemandePublicationForm
from .forms import DonForm
from .forms import EvenementForm

from .models import Abonnement
from .models import BilletEvenement
from .models import DemandePublication
from .models import Don
from .models import Evenement  
from datetime import timedelta

from django.utils import timezone
from decimal import Decimal

from .models import (
    Evenement,
    PaiementFraisEvenement,
    NotificationEvenement,
)

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
from .forms import (
    PaiementFraisEvenementForm,
)

from .models import (
    PaiementFraisEvenement,
)

import mimetypes
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import AchatTelechargementVideoForm
from .models import AchatTelechargementVideo, Video
from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Value
from django.db.models import When
from functools import partial

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import VideoForm
from .models import Musique
from functools import partial


from .services_video import traiter_video
from django.db.models import Exists, OuterRef
from django.shortcuts import render



def videos_publiques():

    return (
        Video.objects
        .filter(est_publiee=True)
        .select_related(
            "auteur",
            "auteur__profil",
        )
        .annotate(
            nombre_jaimes=Count(
                "jaimes",
                distinct=True,
            ),
            nombre_commentaires=Count(
                "commentaires",
                filter=Q(
                    commentaires__est_visible=True
                ),
                distinct=True,
            ),
        )
    )




# ============================================================
# AFROFANS — FLUX VIDÉOS + PRÉSENCES EN DIRECT
# ============================================================

from django.shortcuts import render

from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
)

from .models import (
    Abonnement,
    Jaime,
    Favori,
    PresenceAfroFans,
)

# Conserver ton import existant de videos_publiques.


def flux(request):

    # --------------------------------------------------------
    # 1. ONGLET ACTIF
    # --------------------------------------------------------

    onglet = request.GET.get(
        "onglet",
        "pour-toi"
    )

    # Accepter également l'ancien nom de l'onglet.
    if onglet == "suivis":
        onglet = "talents"

    if onglet not in (
        "pour-toi",
        "talents",
    ):
        onglet = "pour-toi"

    # --------------------------------------------------------
    # 2. VIDÉOS PUBLIQUES
    # --------------------------------------------------------

    videos = videos_publiques()

    videos = videos.annotate(

        nombre_jaimes=Count(
            "jaimes",
            distinct=True,
        ),

        nombre_commentaires=Count(
            "commentaires",
            filter=Q(
                commentaires__est_visible=True
            ),
            distinct=True,
        ),

        nombre_favoris=Count(
            "favoris",
            distinct=True,
        ),
    )

    # --------------------------------------------------------
    # 3. PRÉSENCES ACTIVES
    # --------------------------------------------------------

    presences = (
        PresenceAfroFans.objects
        .filter(
            est_active=True
        )
        .select_related(
            "talent",
            "talent__profil",
        )
        .order_by("-cree_le")
    )

    # --------------------------------------------------------
    # 4. UTILISATEUR CONNECTÉ
    # --------------------------------------------------------

    if request.user.is_authenticated:

        abonnement_existant = (
            Abonnement.objects.filter(
                fan=request.user,
                createur_id=OuterRef("auteur_id"),
            )
        )

        jaime_existant = (
            Jaime.objects.filter(
                utilisateur=request.user,
                video_id=OuterRef("pk"),
            )
        )

        favori_existant = (
            Favori.objects.filter(
                utilisateur=request.user,
                video_id=OuterRef("pk"),
            )
        )

        videos = videos.annotate(

            est_abonne=Exists(
                abonnement_existant
            ),

            est_aime=Exists(
                jaime_existant
            ),

            est_favori=Exists(
                favori_existant
            ),
        )

        # ----------------------------------------------------
        # 5. ONGLET TALENTS
        # ----------------------------------------------------

        if onglet == "talents":

            createurs_suivis = (
                Abonnement.objects
                .filter(
                    fan=request.user
                )
                .values_list(
                    "createur_id",
                    flat=True
                )
            )

            videos = videos.filter(
                auteur_id__in=createurs_suivis
            )

            presences = presences.filter(
                talent_id__in=createurs_suivis
            )

    # --------------------------------------------------------
    # 6. VISITEUR NON CONNECTÉ
    # --------------------------------------------------------

    elif onglet == "talents":

        videos = videos.none()
        presences = presences.none()

    # --------------------------------------------------------
    # 7. MÉLANGER VIDÉOS ET PRÉSENCES
    # --------------------------------------------------------
    #
    # Une présence est insérée après trois vidéos.
    # Les présences supplémentaires sont affichées à la fin.
    #
    # Chaque élément indique son type :
    # - video
    # - presence
    # --------------------------------------------------------

    liste_videos = list(videos)
    liste_presences = list(presences)

    elements_flux = []

    index_presence = 0

    for index, video in enumerate(liste_videos):

        elements_flux.append({
            "type": "video",
            "video": video,
            "presence": None,
        })

        # Insérer une présence toutes les trois vidéos.

        if (
            (index + 1) % 3 == 0
            and index_presence < len(liste_presences)
        ):

            elements_flux.append({
                "type": "presence",
                "video": None,
                "presence": liste_presences[index_presence],
            })

            index_presence += 1

    # Afficher les présences restantes, même si aucune
    # vidéo n'est disponible.

    while index_presence < len(liste_presences):

        elements_flux.append({
            "type": "presence",
            "video": None,
            "presence": liste_presences[index_presence],
        })

        index_presence += 1

    # --------------------------------------------------------
    # 8. CONTEXTE
    # --------------------------------------------------------

    contexte = {

        "videos": videos,

        "presences_actives": liste_presences,

        "elements_flux": elements_flux,

        "nombre_presences": len(liste_presences),

        "onglet": onglet,
    }

    # --------------------------------------------------------
    # 9. AFFICHAGE
    # --------------------------------------------------------

    return render(
        request,
        "Afrons/flux.html",
        contexte,
    )



def explorer(request):

    recherche = request.GET.get(
        "q",
        "",
    ).strip()

    categorie = request.GET.get(
        "categorie",
        "",
    )

    videos = videos_publiques()

    if recherche:

        videos = videos.filter(

            Q(titre__icontains=recherche)

            | Q(
                description__icontains=recherche
            )

            | Q(
                hashtags__icontains=recherche
            )

            | Q(
                auteur__username__icontains=(
                    recherche
                )
            )

            | Q(
                auteur__profil__nom_scene__icontains=(
                    recherche
                )
            )
        )

    if categorie:

        videos = videos.filter(
            categorie=categorie
        )

    contexte = {

        "videos": videos,

        "recherche": recherche,

        "categorie_active": categorie,

        "categories": Video.CATEGORIES,
    }

    return render(
        request,
        "Afrons/explorer.html",
        contexte,
    )




def inscription(request):

    if request.user.is_authenticated:
        return redirect(
            "Afrons:flux"
        )

    # La photo n’est plus demandée à l’inscription.
    formulaire = InscriptionForm(
        request.POST or None,
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        utilisateur = formulaire.save()

        login(
            request,
            utilisateur,
        )

        type_compte = (
            utilisateur.profil.type_compte
        )

        if type_compte == "createur":

            messages.success(
                request,
                (
                    "Bienvenue sur AfroFans ! "
                    "Ton compte Créateur a été créé. "
                    "Ajoute maintenant ta photo et "
                    "complète ton profil."
                ),
            )

            return redirect(
                "Afrons:modifier_profil"
            )

        messages.success(
            request,
            (
                "Bienvenue sur AfroFans ! "
                "Ton compte Fan a été créé. "
                "Découvre les créateurs et "
                "soutiens tes artistes préférés."
            ),
        )

        return redirect(
            "Afrons:flux"
        )

    return render(
        request,
        "Afrons/inscription.html",
        {
            "formulaire": formulaire,
        },
    )











def connexion(request):

    if request.user.is_authenticated:

        return redirect(
            "Afrons:flux"
        )

    formulaire = AuthenticationForm(

        request,

        data=request.POST or None,
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        login(
            request,
            formulaire.get_user(),
        )

        destination = request.GET.get(
            "next"
        )

        return redirect(
            destination or "Afrons:flux"
        )

    return render(
        request,
        "Afrons/connexion.html",
        {
            "formulaire": formulaire,
        },
    )


@require_POST
def deconnexion(request):

    logout(request)

    return redirect(
        "Afrons:flux"
    )


# ============================================================
# AFROFANS — PUBLICATION VIDÉO
# PostgreSQL + Cloudinary + AfroFans Studio
# ============================================================

@login_required
def publier_video(request):

    # ========================================================
    # 1. VÉRIFICATION DU PROFIL
    # ========================================================

    profil = request.user.profil

    if profil.type_compte != "createur":

        messages.error(
            request,
            (
                "Seuls les comptes Talent peuvent "
                "publier des vidéos sur AfroFans."
            ),
        )

        return redirect("Afrons:flux")

    # ========================================================
    # 2. MUSIQUES DISPONIBLES
    # ========================================================

    musiques = (
        Musique.objects
        .filter(
            est_active=True,
            est_autorisee=True,
        )
        .order_by(
            "-est_populaire",
            "-nombre_utilisations",
            "titre",
        )
    )

    # ========================================================
    # 3. FORMULAIRE DE PUBLICATION
    # ========================================================

    formulaire = VideoForm(
        request.POST or None,
        request.FILES or None,
    )

    # ========================================================
    # 4. PUBLICATION
    # ========================================================

    if request.method == "POST":

        if formulaire.is_valid():

            # ------------------------------------------------
            # MODE MUSICAL
            # ------------------------------------------------

            mode_musique = request.POST.get(
                "selection_musique",
                "automatique",
            )

            modes_autorises = (
                "automatique",
                "manuelle",
                "original",
            )

            if mode_musique not in modes_autorises:
                mode_musique = "automatique"

            # =================================================
            # 5. PRÉPARATION DE LA VIDÉO
            # =================================================

            video = formulaire.save(commit=False)

            video.auteur = request.user

            # ------------------------------------------------
            # MUSIQUE AUTOMATIQUE
            # ------------------------------------------------

            if (
                mode_musique == "automatique"
                and not video.musique_id
            ):

                video.musique = (
                    musique_recommandee_pour_categorie(
                        video.categorie
                    )
                )

            # ------------------------------------------------
            # SON ORIGINAL
            # ------------------------------------------------

            if mode_musique == "original":

                video.musique = None
                video.volume_musique = 0

            # ------------------------------------------------
            # VÉRIFICATION MUSIQUE
            # ------------------------------------------------

            if video.musique_id:

                musique_valide = (
                    video.musique.est_active
                    and video.musique.est_autorisee
                )

                if not musique_valide:

                    video.musique = None
                    video.volume_musique = 0

            # =================================================
            # 6. STATUT INITIAL
            # =================================================

            video.statut_traitement = "en_attente"

            video.erreur_traitement = ""

            # Ne pas afficher publiquement une vidéo
            # avant la réussite du traitement.

            video.est_publiee = False

            # =================================================
            # 7. ENREGISTREMENT CLOUDINARY + POSTGRESQL
            # =================================================

            try:

                with transaction.atomic():

                    video.save()

                    # Enregistrer les relations ManyToMany
                    # éventuelles du formulaire.

                    formulaire.save_m2m()

            except Exception:

                logger.exception(
                    "AfroFans : échec de l'enregistrement "
                    "de la vidéo de l'utilisateur %s",
                    request.user.pk,
                )

                messages.error(
                    request,
                    (
                        "Impossible d'enregistrer la vidéo. "
                        "Vérifie le fichier envoyé et "
                        "réessaie."
                    ),
                )

                return render(
                    request,
                    "Afrons/publier_video.html",
                    {
                        "formulaire": formulaire,
                        "musiques": musiques,
                    },
                )

            # =================================================
            # 8. TRAITEMENT AFROFANS STUDIO
            # =================================================

            traitement_reussi = False

            try:

                traitement_reussi = traiter_video(
                    video.pk
                )

            except Exception as erreur:

                logger.exception(
                    "AfroFans Studio : échec du "
                    "traitement de la vidéo %s",
                    video.pk,
                )

                # Conserver un diagnostic interne.
                # Ne pas exposer les détails techniques
                # au public.

                Video.objects.filter(
                    pk=video.pk
                ).update(
                    statut_traitement="echec",
                    erreur_traitement=str(erreur)[:2000],
                    est_publiee=False,
                )

                traitement_reussi = False

            # =================================================
            # 9. VÉRIFIER LE RÉSULTAT DU MONTAGE
            # =================================================

            video.refresh_from_db()

            if traitement_reussi:

                # Vérification du fichier final.
                # La méthode traiter_video doit avoir
                # enregistré la version traitée.

                if (
                    video.statut_traitement == "termine"
                    and video.fichier_traite
                ):

                    messages.success(
                        request,
                        (
                            "Ta vidéo a été préparée "
                            "avec succès ! La musique "
                            "et les filtres ont été "
                            "intégrés par AfroFans Studio."
                        ),
                    )

                else:

                    logger.error(
                        "AfroFans Studio : vidéo %s "
                        "annoncée réussie mais résultat "
                        "incomplet.",
                        video.pk,
                    )

                    traitement_reussi = False

                    Video.objects.filter(
                        pk=video.pk
                    ).update(
                        statut_traitement="echec",
                        erreur_traitement=(
                            "Traitement annoncé terminé "
                            "mais fichier final absent "
                            "ou statut incorrect."
                        ),
                        est_publiee=False,
                    )

            # =================================================
            # 10. ÉCHEC DU MONTAGE
            # =================================================

            if not traitement_reussi:

                # Si le service a retourné False sans
                # renseigner l'erreur, conserver un
                # diagnostic générique dans la base.

                video.refresh_from_db()

                if video.statut_traitement != "echec":

                    Video.objects.filter(
                        pk=video.pk
                    ).update(
                        statut_traitement="echec",
                        est_publiee=False,
                    )

                if not video.erreur_traitement:

                    Video.objects.filter(
                        pk=video.pk
                    ).update(
                        erreur_traitement=(
                            "AfroFans Studio n'a pas "
                            "terminé le montage. "
                            "Consulter les journaux "
                            "du traitement vidéo."
                        )
                    )

                logger.error(
                    "AfroFans Studio : montage échoué "
                    "pour la vidéo %s",
                    video.pk,
                )

                messages.warning(
                    request,
                    (
                        "Ta vidéo originale a bien été "
                        "enregistrée, mais AfroFans Studio "
                        "n'a pas réussi à terminer le "
                        "montage. La vidéo reste privée "
                        "en attendant la correction."
                    ),
                )

            # =================================================
            # 11. REDIRECTION VERS LA VIDÉO
            # =================================================

            return redirect(
                "Afrons:detail_video",
                video_id=video.pk,
            )

        # =====================================================
        # 12. FORMULAIRE INVALIDE
        # =====================================================

        logger.warning(
            "AfroFans : formulaire vidéo invalide "
            "pour l'utilisateur %s : %s",
            request.user.pk,
            formulaire.errors.as_json(),
        )

        messages.error(
            request,
            (
                "La vidéo n'a pas été envoyée. "
                "Vérifie les champs indiqués "
                "dans le formulaire."
            ),
        )

    # ========================================================
    # 13. AFFICHER LE FORMULAIRE
    # ========================================================

    return render(
        request,
        "Afrons/publier_video.html",
        {
            "formulaire": formulaire,
            "musiques": musiques,
        },
    )


from django.shortcuts import (
    render,
    get_object_or_404,
)

from django.db.models import Q, F


def detail_video(request, video_id):

    # =====================================================
    # 1. VIDÉOS ACCESSIBLES
    # =====================================================

    videos_accessibles = (
        Video.objects
        .select_related(
            "auteur",
            "auteur__profil",
            "musique",
        )
    )

    if request.user.is_authenticated:

        # Vidéos publiques + vidéos de l'utilisateur
        videos_accessibles = videos_accessibles.filter(
            Q(est_publiee=True)
            | Q(auteur=request.user)
        )

    else:

        # Visiteurs : vidéos publiées uniquement
        videos_accessibles = videos_accessibles.filter(
            est_publiee=True
        )

    video = get_object_or_404(
        videos_accessibles,
        pk=video_id,
    )

    # =====================================================
    # 2. VÉRIFIER LE PROPRIÉTAIRE
    # =====================================================

    est_proprietaire = (
        request.user.is_authenticated
        and video.auteur_id == request.user.pk
    )

    # =====================================================
    # 3. COMPTEUR DE VUES
    # =====================================================

    # Le propriétaire ne génère pas de vue
    # sur sa propre vidéo.

    if (
        video.est_publiee
        and not est_proprietaire
    ):

        Video.objects.filter(
            pk=video.pk
        ).update(
            vues=F("vues") + 1
        )

        video.refresh_from_db(
            fields=["vues"]
        )

    # =====================================================
    # 4. COMMENTAIRES VISIBLES
    # =====================================================

    commentaires = (
        video.commentaires
        .filter(
            est_visible=True
        )
        .select_related(
            "utilisateur",
            "utilisateur__profil",
        )
        .order_by("-cree_le")
    )

    # =====================================================
    # 5. NOMBRE RÉEL DE J'AIME
    # =====================================================

    # Même modèle Jaime que dans le Flux.
    # Le nombre reste donc identique entre les pages.

    nombre_jaimes = Jaime.objects.filter(
        video=video,
    ).count()

    # =====================================================
    # 6. NOMBRE RÉEL DE COMMENTAIRES
    # =====================================================

    nombre_commentaires = commentaires.count()

    # =====================================================
    # 7. NOMBRE DE PARTAGES
    # =====================================================

    # Nécessite le champ nombre_partages
    # dans le modèle Video.

    nombre_partages = video.nombre_partages

    # =====================================================
    # 8. INTERACTIONS DE L'UTILISATEUR
    # =====================================================

    utilisateur_aime = False
    utilisateur_favori = False
    est_abonne = False

    if request.user.is_authenticated:

        # -----------------------------------------------
        # J'AIME DÉJÀ ENREGISTRÉ
        # -----------------------------------------------

        utilisateur_aime = Jaime.objects.filter(
            utilisateur=request.user,
            video=video,
        ).exists()

        # -----------------------------------------------
        # FAVORI DÉJÀ ENREGISTRÉ
        # -----------------------------------------------

        utilisateur_favori = Favori.objects.filter(
            utilisateur=request.user,
            video=video,
        ).exists()

        # -----------------------------------------------
        # VÉRIFIER SI L'UTILISATEUR EST FAN
        # -----------------------------------------------

        if not est_proprietaire:

            est_abonne = Abonnement.objects.filter(
                fan=request.user,
                createur=video.auteur,
            ).exists()

    # =====================================================
    # 9. POLITIQUE OFFICIELLE AFROFANS
    # =====================================================

    # Le propriétaire télécharge gratuitement.
    # Les autres utilisateurs doivent payer.

    telechargement_gratuit = est_proprietaire

    # Seul le propriétaire peut supprimer la vidéo.

    peut_supprimer = est_proprietaire

    # =====================================================
    # 10. TRAITEMENT DE LA VIDÉO
    # =====================================================

    traitement_en_cours = (
        video.statut_traitement
        in (
            "en_attente",
            "traitement",
        )
    )

    traitement_echec = (
        video.statut_traitement == "echec"
    )

    # =====================================================
    # 11. CONTEXTE COMPLET
    # =====================================================

    contexte = {

        # Vidéo
        "video": video,

        # Commentaires
        "commentaires": commentaires,

        "formulaire_commentaire": (
            CommentaireForm()
        ),

        # -----------------------------------------------
        # COMPTEURS RÉELS
        # -----------------------------------------------

        "nombre_jaimes": nombre_jaimes,

        "nombre_commentaires": nombre_commentaires,

        "nombre_partages": nombre_partages,

        # -----------------------------------------------
        # ÉTAT DES INTERACTIONS
        # -----------------------------------------------

        "utilisateur_aime": utilisateur_aime,

        "utilisateur_favori": utilisateur_favori,

        # -----------------------------------------------
        # DEVENIR FAN
        # -----------------------------------------------

        "est_abonne": est_abonne,

        # -----------------------------------------------
        # DROITS DU PROPRIÉTAIRE
        # -----------------------------------------------

        "est_proprietaire": est_proprietaire,

        "telechargement_gratuit": (
            telechargement_gratuit
        ),

        "peut_supprimer": peut_supprimer,

        # -----------------------------------------------
        # TRAITEMENT VIDÉO
        # -----------------------------------------------

        "traitement_en_cours": (
            traitement_en_cours
        ),

        "traitement_echec": (
            traitement_echec
        ),
    }

    # =====================================================
    # 12. AFFICHAGE DE LA PAGE
    # =====================================================

    return render(
        request,
        "Afrons/detail_video.html",
        contexte,
    )


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect


# ============================================================
# AFROFANS — SUPPRESSION SÉCURISÉE D'UNE VIDÉO
# ============================================================

@login_required
@require_POST
def supprimer_video(request, video_id):

    # Seul l'auteur propriétaire peut accéder
    # à cette vidéo pour la supprimer.

    video = get_object_or_404(
        Video,
        pk=video_id,
        auteur=request.user,
    )

    video.delete()

    messages.success(
        request,
        "Votre vidéo a été supprimée avec succès."
    )

    return redirect("Afrons:flux")



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import F
from django.shortcuts import get_object_or_404


@require_POST
def enregistrer_partage_video(request, video_id):

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
    )

    Video.objects.filter(
        pk=video.pk
    ).update(
        nombre_partages=F("nombre_partages") + 1
    )

    video.refresh_from_db(
        fields=["nombre_partages"]
    )

    return JsonResponse({
        "success": True,
        "total": video.nombre_partages,
    })


from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render

from .models_certification_afrofans import (
    CertificationCompteAfroFans,
)
from .models_notifications_afrofans import (
    NotificationOfficielleAfroFans,
)


def profil_public(request, username):

    Utilisateur = get_user_model()

    # ========================================================
    # 1. RÉCUPÉRER LE PROFIL
    # ========================================================

    personne = get_object_or_404(
        Utilisateur.objects.select_related("profil"),
        username=username,
    )

    profil = personne.profil

    est_proprietaire = (
        request.user.is_authenticated
        and request.user.pk == personne.pk
    )

    # ========================================================
    # 2. VIDÉOS PUBLIQUES
    # ========================================================

    videos = videos_publiques().filter(
        auteur=personne,
    )

    # ========================================================
    # 3. ABONNEMENT AU TALENT
    # ========================================================

    est_abonne = False

    if (
        request.user.is_authenticated
        and not est_proprietaire
    ):

        est_abonne = Abonnement.objects.filter(
            fan=request.user,
            createur=personne,
        ).exists()

    # ========================================================
    # 4. ÉVÉNEMENTS DU TALENT
    # ========================================================

    evenements = (
        Evenement.objects
        .filter(createur=personne)
        .select_related(
            "createur",
            "createur__profil",
        )
        .order_by("-date_evenement")
    )

    # Les visiteurs voient uniquement les événements
    # publiés avec les frais de billetterie confirmés.

    if not est_proprietaire:

        evenements = evenements.filter(
            statut__in=("publie", "ouvert"),
            frais_billetterie_payes=True,
        )

    # ========================================================
    # 5. CERTIFICATION DU COMPTE
    # ========================================================

    certification = (
        CertificationCompteAfroFans.objects
        .filter(utilisateur=personne)
        .first()
    )

    statut_certification = (
        certification.statut
        if certification
        else "non_certifie"
    )

    est_certifie = (
        statut_certification == "certifie"
    )

    certification_en_attente = (
        statut_certification == "en_verification"
    )

    peut_certifier = (
        est_proprietaire
        and not est_certifie
        and not certification_en_attente
    )

    # Prix de certification en dollars canadiens

    prix_certification = "15.00"

    tps_certification = "0.75"

    tvq_certification = "1.50"

    total_certification_quebec = "17.25"

    # ========================================================
    # 6. DONS REÇUS
    # ========================================================

    dons_recus = Don.objects.none()

    total_dons_payes = 0

    # ========================================================
    # 7. BILLETS ACHETÉS
    # ========================================================

    achats_billets = BilletEvenement.objects.none()

    # ========================================================
    # 8. NOTIFICATIONS EXISTANTES
    # ========================================================

    notifications = NotificationEvenement.objects.none()

    notifications_officielles = (
        NotificationOfficielleAfroFans.objects.none()
    )

    notifications_non_lues = 0

    # Les données privées sont exclusivement
    # accessibles au propriétaire du compte.

    if est_proprietaire:

        # ----------------------------------------------------
        # TALENT OU ORGANISATEUR
        # ----------------------------------------------------

        if profil.type_compte in (
            "createur",
            "organisateur",
        ):

            dons_recus = (
                Don.objects
                .filter(createur=personne)
                .select_related(
                    "donateur",
                    "donateur__profil",
                )
                .order_by("-cree_le")
            )

            total_dons_payes = dons_recus.filter(
                statut="paye",
            ).count()

        # ----------------------------------------------------
        # FAN
        # ----------------------------------------------------

        if profil.type_compte == "fan":

            achats_billets = (
                BilletEvenement.objects
                .filter(acheteur=personne)
                .select_related(
                    "evenement",
                    "evenement__createur",
                    "evenement__createur__profil",
                )
                .order_by("-cree_le")
            )

        # ----------------------------------------------------
        # NOTIFICATIONS D'ÉVÉNEMENTS
        # ----------------------------------------------------

        notifications = (
            NotificationEvenement.objects
            .filter(destinataire=personne)
            .select_related(
                "evenement",
                "evenement__createur",
                "evenement__createur__profil",
            )
            .order_by("-cree_le")
        )

        # ----------------------------------------------------
        # NOTIFICATIONS OFFICIELLES AFROFANS
        # ----------------------------------------------------

        notifications_officielles = (
            NotificationOfficielleAfroFans.objects
            .filter(destinataire=personne)
            .select_related(
                "evenement",
                "evenement__createur",
            )
            .order_by("-cree_le")
        )

        notifications_non_lues = (
            notifications.filter(
                est_lue=False
            ).count()
            +
            notifications_officielles.filter(
                est_lue=False
            ).count()
        )

    # ========================================================
    # 9. PRÉSENCE ACTIVE DU TALENT
    # ========================================================

    presence_active = None

    # La présence est réservée aux comptes Talent.
    # Un Fan ou un Organisateur n'affiche pas le
    # cercle rouge de présence d'un Talent.

    if profil.type_compte == "createur":

        presence_active = (
            PresenceAfroFans.objects
            .filter(
                talent=personne,
                est_active=True,
            )
            .order_by("-cree_le")
            .first()
        )

    # Le cercle rouge doit apparaître seulement
    # lorsqu'une présence est réellement active.

    est_en_presence = (
        presence_active is not None
    )

    # ========================================================
    # 10. CONTEXTE COMPLET DU PROFIL
    # ========================================================

    contexte = {

        # ----------------------------------------------------
        # PROFIL
        # ----------------------------------------------------

        "personne": personne,

        "profil": profil,

        # Alias pour les templates utilisant
        # profil_utilisateur pour désigner le User.

        "profil_utilisateur": personne,

        "est_proprietaire": est_proprietaire,

        # ----------------------------------------------------
        # VIDÉOS
        # ----------------------------------------------------

        "videos": videos,

        # ----------------------------------------------------
        # ABONNEMENTS
        # ----------------------------------------------------

        "est_abonne": est_abonne,

        # ----------------------------------------------------
        # ÉVÉNEMENTS
        # ----------------------------------------------------

        "evenements": evenements,

        # ----------------------------------------------------
        # DONS
        # ----------------------------------------------------

        "dons_recus": dons_recus,

        "total_dons_payes": total_dons_payes,

        # ----------------------------------------------------
        # BILLETS
        # ----------------------------------------------------

        "achats_billets": achats_billets,

        # ----------------------------------------------------
        # NOTIFICATIONS
        # ----------------------------------------------------

        "notifications": notifications,

        "notifications_officielles": (
            notifications_officielles
        ),

        "notifications_non_lues": (
            notifications_non_lues
        ),

        # ----------------------------------------------------
        # CERTIFICATION
        # ----------------------------------------------------

        "certification": certification,

        "statut_certification": (
            statut_certification
        ),

        "est_certifie": est_certifie,

        "certification_en_attente": (
            certification_en_attente
        ),

        "peut_certifier": peut_certifier,

        # ----------------------------------------------------
        # PRIX DE CERTIFICATION
        # ----------------------------------------------------

        "prix_certification": prix_certification,

        "tps_certification": tps_certification,

        "tvq_certification": tvq_certification,

        "total_certification_quebec": (
            total_certification_quebec
        ),

        # ----------------------------------------------------
        # NOUVEAU — PRÉSENCE AFROFANS
        # ----------------------------------------------------

        "presence_active": presence_active,

        "est_en_presence": est_en_presence,
    }

    # ========================================================
    # 11. AFFICHER LE PROFIL PUBLIC
    # ========================================================

    return render(
        request,
        "Afrons/profil.html",
        contexte,
    )







@login_required
def modifier_profil(request):

    formulaire_utilisateur = UtilisateurForm(
        request.POST or None,
        instance=request.user,
    )

    formulaire_profil = ProfilForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user.profil,
    )

    if (
        request.method == "POST"
        and formulaire_utilisateur.is_valid()
        and formulaire_profil.is_valid()
    ):
        formulaire_utilisateur.save()

        formulaire_profil.save()

        messages.success(
            request,
            "Ton profil a été mis à jour avec succès.",
        )

        return redirect(
            "Afrons:profil_public",
            username=request.user.username,
        )

    return render(
        request,
        "Afrons/modifier_profil.html",
        {
            "formulaire_utilisateur": (
                formulaire_utilisateur
            ),
            "formulaire_profil": (
                formulaire_profil
            ),
        },
    )




@login_required
@require_POST
def aimer_video(request, video_id):

    # ========================================================
    # 1. RÉCUPÉRER LA VIDÉO PUBLIÉE
    # ========================================================

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
    )

    # ========================================================
    # 2. AJOUTER OU RETIRER LE J'AIME
    # ========================================================

    with transaction.atomic():

        jaime = Jaime.objects.filter(
            utilisateur=request.user,
            video=video,
        )

        if jaime.exists():

            # L'utilisateur a déjà aimé :
            # on retire son J'aime.

            jaime.delete()

            actif = False

            message = (
                "Vous avez retiré votre J’aime."
            )

        else:

            # L'utilisateur n'a pas encore aimé :
            # on ajoute son J'aime.

            Jaime.objects.create(
                utilisateur=request.user,
                video=video,
            )

            actif = True

            message = (
                "Vous aimez cette vidéo."
            )

        # ====================================================
        # 3. CALCULER LE VRAI NOMBRE DE J'AIME
        # ====================================================

        total = Jaime.objects.filter(
            video=video,
        ).count()

    # ========================================================
    # 4. RÉPONSE AJAX POUR FLUX ET DÉTAIL
    # ========================================================

    return JsonResponse({
        "success": True,
        "actif": actif,
        "total": total,
        "message": message,
    })


@login_required
@require_POST
def ajouter_favori(request, video_id):

    video = get_object_or_404(
        Video,
        id=video_id,
        est_publiee=True,
    )

    favori = Favori.objects.filter(
        utilisateur=request.user,
        video=video,
    )

    if favori.exists():

        favori.delete()

        actif = False

    else:

        Favori.objects.create(
            utilisateur=request.user,
            video=video,
        )

        actif = True

    return JsonResponse(
        {
            "actif": actif,
        }
    )


@login_required
@require_POST
def commenter_video(request, video_id):

    video = get_object_or_404(
        Video,
        id=video_id,
        est_publiee=True,
    )

    if not video.autoriser_commentaires:

        messages.error(
            request,
            "Les commentaires sont désactivés.",
        )

        return redirect(
            video.get_absolute_url()
        )

    formulaire = CommentaireForm(
        request.POST
    )

    if formulaire.is_valid():

        commentaire = formulaire.save(
            commit=False
        )

        commentaire.utilisateur = (
            request.user
        )

        commentaire.video = video

        commentaire.save()

    return redirect(
        video.get_absolute_url()
    )


@login_required
@require_POST
def suivre_createur(request, username):

    createur = get_object_or_404(
        User,
        username=username,
    )

    if createur == request.user:

        return JsonResponse(
            {
                "erreur": (
                    "Tu ne peux pas te suivre."
                )
            },
            status=400,
        )

    abonnement = Abonnement.objects.filter(
        fan=request.user,
        createur=createur,
    )

    if abonnement.exists():

        abonnement.delete()

        actif = False

    else:

        Abonnement.objects.create(
            fan=request.user,
            createur=createur,
        )

        actif = True

    return JsonResponse(
        {
            "actif": actif,
            "total": createur.abonnes.count(),
        }
    )


@login_required
def signaler_video(request, video_id):

    video = get_object_or_404(
        Video,
        id=video_id,
    )

    formulaire = SignalementForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        Signalement.objects.update_or_create(

            auteur=request.user,

            video=video,

            defaults=formulaire.cleaned_data,
        )

        messages.success(
            request,
            (
                "Le signalement a été transmis "
                "à la modération."
            ),
        )

        return redirect(
            video.get_absolute_url()
        )

    return render(
        request,
        "Afrons/signaler_video.html",
        {
            "video": video,
            "formulaire": formulaire,
        },
    )



def liste_abonnes(request, username):

    personne = get_object_or_404(
        User.objects.select_related(
            "profil"
        ),
        username=username,
    )

    relations = (
        Abonnement.objects
        .filter(createur=personne)
        .select_related(
            "fan",
            "fan__profil",
        )
    )

    membres = [
        relation.fan
        for relation in relations
    ]

    return render(
        request,
        "Afrons/liste_membres.html",
        {
            "personne": personne,
            "membres": membres,
            "titre": "Abonnés",
        },
    )


def liste_abonnements(
    request,
    username,
):

    personne = get_object_or_404(
        User.objects.select_related(
            "profil"
        ),
        username=username,
    )

    relations = (
        Abonnement.objects
        .filter(fan=personne)
        .select_related(
            "createur",
            "createur__profil",
        )
    )

    membres = [
        relation.createur
        for relation in relations
    ]

    return render(
        request,
        "Afrons/liste_membres.html",
        {
            "personne": personne,
            "membres": membres,
            "titre": "Abonnements",
        },
    )


@login_required
def envoyer_don(
    request,
    username,
):

    createur = get_object_or_404(
        User.objects.select_related(
            "profil"
        ),
        username=username,
        profil__type_compte="createur",
    )

    if createur == request.user:
        messages.error(
            request,
            (
                "Tu ne peux pas envoyer "
                "un don à ton propre compte."
            ),
        )

        return redirect(
            "Afrons:profil_public",
            username=createur.username,
        )

    formulaire = DonForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        don = formulaire.save(
            commit=False
        )

        don.donateur = request.user
        don.createur = createur
        don.statut = "en_attente"
        don.save()

        messages.success(
            request,
            (
                "Ta demande de don a été créée. "
                "Le paiement est en attente."
            ),
        )

        return redirect(
            "Afrons:confirmation_don",
            reference=don.reference,
        )

    return render(
        request,
        "Afrons/envoyer_don.html",
        {
            "formulaire": formulaire,
            "createur": createur,
        },
    )


@login_required
def confirmation_don(
    request,
    reference,
):

    don = get_object_or_404(
        Don.objects.select_related(
            "createur",
            "createur__profil",
        ),
        reference=reference,
        donateur=request.user,
    )

    return render(
        request,
        "Afrons/confirmation_don.html",
        {
            "don": don,
        },
    )




@login_required
@transaction.atomic
def creer_evenement(request):

    if (
        not hasattr(request.user, "profil")
        or request.user.profil.type_compte
        != "createur"
    ):
        messages.error(
            request,
            (
                "Seuls les créateurs peuvent "
                "créer un événement."
            ),
        )

        return redirect(
            "Afrons:flux"
        )

    formulaire = EvenementForm(
        request.POST or None,
        request.FILES or None,
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        evenement = formulaire.save(
            commit=False
        )

        evenement.createur = (
            request.user
        )

        evenement.statut = (
            "paiement_attente"
        )

        evenement.save()

        paiement = (
            PaiementFraisEvenement
            .objects.create(
                evenement=evenement,
                createur=request.user,
                devise_paiement="XOF",
                taux_conversion=Decimal(
                    "1"
                ),
            )
        )

        messages.success(
            request,
            (
                "Ton événement a été créé. "
                "Paie maintenant les frais de "
                "billetterie pour continuer."
            ),
        )

        return redirect(
            "Afrons:payer_frais_evenement",
            paiement_id=paiement.id,
        )

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,
        },
    )

@login_required
def modifier_evenement(
    request,
    evenement_id,
):

    evenement = get_object_or_404(
        Evenement,
        id=evenement_id,
        createur=request.user,
    )

    if evenement.statut == "termine":
        messages.error(
            request,
            (
                "Un événement terminé ne "
                "peut plus être modifié."
            ),
        )

        return redirect(evenement)

    formulaire = EvenementForm(
        request.POST or None,
        request.FILES or None,
        instance=evenement,
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        evenement = formulaire.save(
            commit=False
        )

        evenement.statut = "en_attente"
        evenement.save()

        messages.success(
            request,
            (
                "Les modifications ont été "
                "envoyées pour validation."
            ),
        )

        return redirect(evenement)

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,
            "titre": "Modifier l’événement",
            "evenement": evenement,
        },
    )




@login_required
def confirmation_billet(
    request,
    code_billet,
):

    billet = get_object_or_404(
        BilletEvenement.objects.select_related(
            "evenement",
        ),
        code_billet=code_billet,
        acheteur=request.user,
    )

    return render(
        request,
        "Afrons/confirmation_billet.html",
        {
            "billet": billet,
        },
    )


@login_required
def demande_publication(request):

    formulaire = DemandePublicationForm(
        request.POST or None,
        request.FILES or None,
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        demande = formulaire.save(
            commit=False
        )

        demande.demandeur = request.user
        demande.statut = "en_attente"
        demande.save()

        messages.success(
            request,
            (
                "Ta demande de publication "
                "a été transmise à AfroFans."
            ),
        )

        return redirect(
            "Afrons:mes_demandes_publication"
        )

    return render(
        request,
        "Afrons/demande_publication.html",
        {
            "formulaire": formulaire,
        },
    )


@login_required
def mes_demandes_publication(
    request,
):

    demandes = (
        DemandePublication.objects
        .filter(demandeur=request.user)
    )

    return render(
        request,
        "Afrons/mes_demandes_publication.html",
        {
            "demandes": demandes,
        },
    )



import json

from datetime import timedelta

from django.db import transaction
from django.http import (
    FileResponse,
    JsonResponse,
)

from django.views.decorators.http import (
    require_POST,
)

from .forms import (
    CodeControleEvenementForm,
    OuvrirScannerForm,
)

from .models import (
    ControleEvenement,
    ControleTicket,
    Evenement,
    TicketEntree,
)

from .services_ticket import (
    construire_pdf_ticket,
)





def est_createur_evenement(
    utilisateur,
    evenement,
):

    return (
        utilisateur.is_authenticated
        and (
            utilisateur
            == evenement.createur
            or utilisateur.is_staff
        )
    )


@login_required
def mes_tickets(request):

    tickets = (
        TicketEntree.objects
        .filter(
            proprietaire=(
                request.user
            )
        )
        .select_related(
            "evenement",
            "commande",
        )
        .order_by(
            "-cree_le"
        )
    )

    return render(
        request,
        "Afrons/mes_tickets.html",
        {
            "tickets": tickets,
        },
    )


@login_required
def telecharger_ticket(
    request,
    identifiant,
):

    ticket = get_object_or_404(
        TicketEntree.objects
        .select_related(
            "evenement",
            "commande",
        ),
        identifiant=identifiant,
        proprietaire=request.user,
        commande__statut="paye",
    )

    pdf = construire_pdf_ticket(
        ticket
    )

    return FileResponse(
        pdf,
        as_attachment=True,
        filename=(
            f"AfroFans-"
            f"{ticket.code_public}.pdf"
        ),
        content_type="application/pdf",
    )


@login_required
def definir_code_controle(
    request,
    evenement_id,
):

    evenement = get_object_or_404(
        Evenement,
        pk=evenement_id,
    )

    if not est_createur_evenement(
        request.user,
        evenement,
    ):

        return JsonResponse(
            {
                "detail": (
                    "Accès refusé."
                ),
            },
            status=403,
        )

    formulaire = (
        CodeControleEvenementForm(
            request.POST or None
        )
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        controle, creation = (
            ControleEvenement.objects
            .get_or_create(
                evenement=evenement
            )
        )

        controle.definir_code_secret(
            formulaire.cleaned_data[
                "code_secret"
            ]
        )

        controle.save()

        messages.success(
            request,
            (
                "Code secret de contrôle "
                "enregistré."
            ),
        )

        return redirect(
            "Afrons:scanner_evenement",
            evenement_id=evenement.id,
        )

    return render(
        request,
        (
            "Afrons/"
            "definir_code_controle.html"
        ),
        {
            "evenement": evenement,
            "formulaire": formulaire,
        },
    )


@login_required
def scanner_evenement(
    request,
    evenement_id,
):

    evenement = get_object_or_404(
        Evenement,
        pk=evenement_id,
    )

    if not est_createur_evenement(
        request.user,
        evenement,
    ):

        return JsonResponse(
            {
                "detail": (
                    "Accès refusé."
                ),
            },
            status=403,
        )

    controle = (
        ControleEvenement.objects
        .filter(
            evenement=evenement
        )
        .first()
    )

    if not controle:

        return redirect(
            "Afrons:definir_code_controle",
            evenement_id=evenement.id,
        )

    cle_session = (
        f"scanner_evenement_"
        f"{evenement.id}"
    )

    autorise_jusqua = (
        request.session.get(
            cle_session
        )
    )

    scanner_ouvert = bool(
        autorise_jusqua
        and autorise_jusqua
        > timezone.now().timestamp()
    )

    formulaire = OuvrirScannerForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        code_secret = (
            formulaire.cleaned_data[
                "code_secret"
            ]
        )

        if controle.verifier_code_secret(
            code_secret
        ):

            expiration = (
                timezone.now()
                + timedelta(hours=2)
            )

            request.session[
                cle_session
            ] = expiration.timestamp()

            scanner_ouvert = True

        else:

            formulaire.add_error(
                "code_secret",
                "Code secret incorrect.",
            )

    return render(
        request,
        (
            "Afrons/"
            "scanner_evenement.html"
        ),
        {
            "evenement": evenement,
            "formulaire": formulaire,
            "scanner_ouvert": (
                scanner_ouvert
            ),
        },
    )


@login_required
@require_POST
@transaction.atomic
def verifier_ticket(
    request,
    evenement_id,
):

    evenement = get_object_or_404(
        Evenement,
        pk=evenement_id,
    )

    if not est_createur_evenement(
        request.user,
        evenement,
    ):

        return JsonResponse(
            {
                "valide": False,
                "message": (
                    "Accès refusé."
                ),
            },
            status=403,
        )

    cle_session = (
        f"scanner_evenement_"
        f"{evenement.id}"
    )

    expiration = request.session.get(
        cle_session,
        0,
    )

    if (
        expiration
        <= timezone.now().timestamp()
    ):

        return JsonResponse(
            {
                "valide": False,
                "message": (
                    "La session du scanner "
                    "a expiré."
                ),
            },
            status=403,
        )

    try:

        donnees = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        donnees = request.POST

    code_recu = str(
        donnees.get(
            "code",
            "",
        )
    ).strip()

    morceaux = code_recu.split(
        ":"
    )

    identifiant = None

    if (
        len(morceaux) == 3
        and morceaux[0]
        == "AFROFANS"
    ):

        identifiant = morceaux[1]
        code_public = morceaux[2]

    else:

        code_public = code_recu

    ticket = (
        TicketEntree.objects
        .select_for_update()
        .select_related(
            "commande",
            "proprietaire",
        )
        .filter(
            evenement=evenement,
            code_public=code_public,
        )
        .first()
    )

    if (
        not ticket
        or (
            identifiant
            and str(
                ticket.identifiant
            ) != identifiant
        )
    ):

        ControleTicket.objects.create(
            evenement=evenement,
            controleur=request.user,
            code_recu=code_recu[:200],
            resultat="invalide",
        )

        return JsonResponse(
            {
                "valide": False,
                "etat": "invalide",
                "message": (
                    "Faux billet ou "
                    "code inconnu."
                ),
            }
        )

    if (
        ticket.commande.statut
        != "paye"
        or ticket.statut
        == "annule"
    ):

        resultat = "annule"

        message = (
            "Billet annulé ou paiement "
            "non confirmé."
        )

        valide = False

    elif ticket.statut == "utilise":

        resultat = "deja_utilise"

        message = (
            "Billet déjà utilisé le "
            f"{ticket.utilise_le:%d/%m/%Y à %H:%M}."
        )

        valide = False

    else:

        ticket.statut = "utilise"

        ticket.utilise_le = (
            timezone.now()
        )

        ticket.controle_par = (
            request.user
        )

        ticket.save(
            update_fields=(
                "statut",
                "utilise_le",
                "controle_par",
            )
        )

        resultat = "accepte"

        message = (
            "Billet authentique. "
            "Entrée autorisée."
        )

        valide = True

    ControleTicket.objects.create(
        evenement=evenement,
        ticket=ticket,
        controleur=request.user,
        code_recu=code_recu[:200],
        resultat=resultat,
    )

    return JsonResponse(
        {
            "valide": valide,
            "etat": resultat,
            "message": message,
            "participant": (
                ticket.nom_participant
            ),
            "numero": (
                f"{ticket.numero}/"
                f"{ticket.commande.quantite}"
            ),
        }
    )





@login_required
def lire_notification_evenement(
    request,
    notification_id,
):
    notification = get_object_or_404(
        NotificationEvenement.objects
        .select_related(
            "evenement",
        ),
        id=notification_id,
        destinataire=request.user,
    )

    if not notification.est_lue:
        notification.est_lue = True

        notification.save(
            update_fields=[
                "est_lue",
            ]
        )

    return redirect(
        "Afrons:detail_evenement",
        evenement_id=(
            notification.evenement_id
        ),
    )




@login_required
@transaction.atomic
def payer_frais_evenement(
    request,
    paiement_id,
):
    paiement = get_object_or_404(
        PaiementFraisEvenement.objects
        .select_for_update()
        .select_related(
            "evenement",
            "createur",
        ),
        id=paiement_id,
        createur=request.user,
    )

    evenement = paiement.evenement

    if evenement.createur != request.user:
        messages.error(
            request,
            (
                "Tu n’as pas l’autorisation "
                "d’accéder à ce paiement."
            ),
        )

        return redirect(
            "Afrons:flux"
        )

    if paiement.statut == "paye":
        messages.info(
            request,
            (
                "Les frais de cet événement "
                "sont déjà payés."
            ),
        )

        return redirect(
            "Afrons:detail_evenement",
            evenement_id=evenement.id,
        )

    formulaire = (
        PaiementFraisEvenementForm(
            request.POST or None,
            initial={
                "devise_paiement": (
                    paiement.devise_paiement
                ),
            },
        )
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):
        devise = formulaire.cleaned_data[
            "devise_paiement"
        ]

        methode = formulaire.cleaned_data[
            "methode_paiement"
        ]

        taux_conversion = Decimal("1")

        if devise == "CAD":
            taux_conversion = Decimal(
                str(
                    getattr(
                        settings,
                        "TAUX_XOF_CAD",
                        "0.00230",
                    )
                )
            )

        elif devise == "EUR":
            taux_conversion = Decimal(
                str(
                    getattr(
                        settings,
                        "TAUX_XOF_EUR",
                        "0.00152449",
                    )
                )
            )

        paiement.devise_paiement = devise
        paiement.taux_conversion = (
            taux_conversion
        )

        # save() recalcule automatiquement
        # le total dans la devise choisie.
        paiement.save()

        request.session[
            f"methode_paiement_frais_"
            f"{paiement.id}"
        ] = methode

        messages.success(
            request,
            (
                "Ta demande de paiement a été "
                "préparée. Le paiement doit être "
                "confirmé avant la validation "
                "de l’événement."
            ),
        )

        return redirect(
            "Afrons:payer_frais_evenement",
            paiement_id=paiement.id,
        )

    contexte = {
        "paiement": paiement,
        "evenement": evenement,
        "formulaire": formulaire,
    }

    return render(
        request,
        "Afrons/payer_frais_evenement.html",
        contexte,
    )




def musique_recommandee_pour_categorie(
    categorie,
):
    correspondances = {
        "musique": [
            "afrobeat",
            "afropop",
            "mandingue",
            "rap",
            "rnb",
        ],
        "danse": [
            "coupe_decale",
            "afrobeat",
            "afropop",
        ],
        "humour": [
            "instrumental",
            "afropop",
        ],
        "mode": [
            "afropop",
            "rnb",
            "afrobeat",
        ],
        "cuisine": [
            "instrumental",
            "traditionnel",
            "afropop",
        ],
        "sport": [
            "rap",
            "afrobeat",
            "instrumental",
        ],
        "art": [
            "instrumental",
            "mandingue",
            "afropop",
        ],
        "culture": [
            "traditionnel",
            "mandingue",
            "instrumental",
        ],
        "education": [
            "instrumental",
            "traditionnel",
        ],
        "autre": [
            "afrobeat",
            "instrumental",
            "autre",
        ],
    }

    categorie = (
        categorie
        or "autre"
    ).strip().lower()

    genres = correspondances.get(
        categorie,
        correspondances["autre"],
    )

    for genre in genres:
        musique = (
            Musique.objects.filter(
                est_active=True,
                est_autorisee=True,
                genre=genre,
            )
            .order_by(
                "-est_populaire",
                "-nombre_utilisations",
            )
            .first()
        )

        if musique:
            return musique

    return (
        Musique.objects.filter(
            est_active=True,
            est_autorisee=True,
        )
        .order_by(
            "-est_populaire",
            "-nombre_utilisations",
        )
        .first()
    )




@login_required
def acheter_telechargement_video(request, video_id):

    # ==========================================
    # 1. RÉCUPÉRER LA VIDÉO PUBLIÉE
    # ==========================================

    video = get_object_or_404(
        Video.objects.select_related(
            "auteur",
            "auteur__profil",
            "musique",
        ),
        pk=video_id,
        est_publiee=True,

        # Accepter les vidéos traitées et
        # celles qui ne nécessitent aucun traitement.
        statut_traitement__in=(
            "termine",
            "non_requis",
        ),
    )

    # ==========================================
    # 2. VÉRIFIER UN ACHAT DÉJÀ PAYÉ
    # ==========================================

    achat_deja_paye = (
        AchatTelechargementVideo.objects
        .filter(
            acheteur=request.user,
            video=video,
            statut="paye",
        )
        .first()
    )

    if achat_deja_paye:
        return redirect(
            "Afrons:confirmation_telechargement_video",
            achat_deja_paye.pk,
        )

    # ==========================================
    # 3. FORMULAIRE D'ACHAT
    # ==========================================

    formulaire = AchatTelechargementVideoForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        devise = formulaire.cleaned_data["devise"]

        methode = formulaire.cleaned_data[
            "methode_paiement"
        ]

        # ======================================
        # 4. CRÉER LA DEMANDE DE PAIEMENT
        # ======================================

        achat, creation = (
            AchatTelechargementVideo.objects
            .get_or_create(
                acheteur=request.user,
                video=video,
                devise=devise,
                defaults={
                    "methode_paiement": methode,
                    "statut": "en_attente",
                },
            )
        )

        if not creation:
            achat.methode_paiement = methode
            achat.save(
                update_fields=["methode_paiement"]
            )

        # ======================================
        # 5. CONFIRMATION DE LA DEMANDE
        # ======================================

        messages.info(
            request,
            (
                "Votre demande de paiement a été "
                "enregistrée. Le téléchargement "
                "sera disponible uniquement après "
                "confirmation du paiement."
            ),
        )

        return redirect(
            "Afrons:confirmation_telechargement_video",
            achat.pk,
        )

    # ==========================================
    # 6. AFFICHER LA PAGE D'ACHAT
    # ==========================================

    return render(
        request,
        "Afrons/acheter_telechargement_video.html",
        {
            "video": video,
            "formulaire": formulaire,
        },
    )


@login_required
def confirmation_telechargement_video(
    request,
    achat_id,
):
    achat = get_object_or_404(
        AchatTelechargementVideo.objects
        .select_related(
            "video",
            "video__auteur",
            "video__auteur__profil",
        ),
        pk=achat_id,
        acheteur=request.user,
    )

    return render(
        request,
        (
            "Afrons/"
            "confirmation_telechargement_video.html"
        ),
        {
            "achat": achat,
            "video": achat.video,
        },
    )


@login_required
def telecharger_video_payee(
    request,
    achat_id,
):
    achat = get_object_or_404(
        AchatTelechargementVideo.objects
        .select_related(
            "video",
            "video__auteur",
        ),
        pk=achat_id,
        acheteur=request.user,
        statut="paye",
    )

    video = achat.video

    fichier = (
        video.fichier_traite
        if video.fichier_traite
        else video.fichier
    )

    if not fichier:
        raise Http404(
            "Le fichier vidéo est introuvable."
        )

    try:
        chemin = Path(fichier.path)

    except (NotImplementedError, ValueError):
        raise Http404(
            "Ce stockage ne permet pas encore "
            "le téléchargement direct."
        )

    if not chemin.exists():
        raise Http404(
            "Le fichier vidéo est introuvable."
        )

    achat.nombre_telechargements += 1

    achat.dernier_telechargement = (
        timezone.now()
    )

    achat.save(
        update_fields=[
            "nombre_telechargements",
            "dernier_telechargement",
        ]
    )

    type_contenu, _ = mimetypes.guess_type(
        chemin.name
    )

    nom_createur = (
        video.auteur.username
        .replace(" ", "-")
    )

    nom_telechargement = (
        f"AfroFans-{nom_createur}-"
        f"{video.pk}{chemin.suffix.lower()}"
    )

    reponse = FileResponse(
        open(chemin, "rb"),
        content_type=(
            type_contenu
            or "application/octet-stream"
        ),
        as_attachment=True,
        filename=nom_telechargement,
    )

    reponse["X-Content-Type-Options"] = (
        "nosniff"
    )

    return reponse





User = get_user_model()


def envoyer_courriel_nouvel_abonne(
    createur,
    nouvel_abonne,
    url_profil,
):
    """
    Envoie un véritable courriel HTML professionnel.
    """

    if not createur.email:
        print(
            "Courriel non envoyé : "
            "le créateur ne possède aucune adresse email."
        )

        return False

    nom_createur = (
        createur.profil.nom_public
        if hasattr(createur, "profil")
        and createur.profil.nom_public
        else createur.username
    )

    nom_abonne = (
        nouvel_abonne.profil.nom_public
        if hasattr(nouvel_abonne, "profil")
        and nouvel_abonne.profil.nom_public
        else nouvel_abonne.username
    )

    nom_createur = escape(nom_createur)
    nom_abonne = escape(nom_abonne)
    username_abonne = escape(
        nouvel_abonne.username
    )
    url_profil = escape(url_profil)

    initiale = (
        nom_abonne[0].upper()
        if nom_abonne
        else "A"
    )

    sujet = (
        f"🎉 {nom_abonne} s’est abonné à ton profil AfroFans"
    )

    message_html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Nouvel abonné AfroFans
        </title>
    </head>

    <body
        style="
            margin: 0;
            padding: 0;
            background-color: #eeeeF3;
            font-family:
                Arial,
                Helvetica,
                sans-serif;
        "
    >
        <table
            role="presentation"
            width="100%"
            cellspacing="0"
            cellpadding="0"
            border="0"
            style="
                width: 100%;
                background-color: #eeeeF3;
            "
        >
            <tr>
                <td
                    align="center"
                    style="
                        padding: 40px 15px;
                    "
                >
                    <table
                        role="presentation"
                        width="600"
                        cellspacing="0"
                        cellpadding="0"
                        border="0"
                        style="
                            width: 100%;
                            max-width: 600px;
                            overflow: hidden;
                            border-radius: 24px;
                            background-color: #ffffff;
                            box-shadow:
                                0 15px 45px
                                rgba(0, 0, 0, 0.12);
                        "
                    >
                        <!-- EN-TÊTE -->

                        <tr>
                            <td
                                align="center"
                                bgcolor="#101010"
                                style="
                                    padding: 36px 25px;
                                    background-color: #101010;
                                "
                            >
                                <table
                                    role="presentation"
                                    cellspacing="0"
                                    cellpadding="0"
                                    border="0"
                                >
                                    <tr>
                                        <td
                                            align="center"
                                            style="
                                                width: 52px;
                                                height: 52px;
                                                border-radius: 16px;
                                                background-color: #ff7900;
                                                color: #ffffff;
                                                font-size: 23px;
                                                font-weight: 900;
                                            "
                                        >
                                            ▶
                                        </td>
                                    </tr>
                                </table>

                                <div
                                    style="
                                        margin-top: 15px;
                                        color: #ffffff;
                                        font-size: 32px;
                                        font-weight: 900;
                                        letter-spacing: -1px;
                                    "
                                >
                                    Afro<span
                                        style="
                                            color: #ff8300;
                                        "
                                    >Fans</span>
                                </div>

                                <div
                                    style="
                                        margin-top: 7px;
                                        color: #bbbbbb;
                                        font-size: 13px;
                                    "
                                >
                                    Partage ton talent.
                                    Inspire ta communauté.
                                </div>
                            </td>
                        </tr>

                        <!-- CONTENU -->

                        <tr>
                            <td
                                align="center"
                                style="
                                    padding: 42px 38px 35px;
                                "
                            >
                                <table
                                    role="presentation"
                                    cellspacing="0"
                                    cellpadding="0"
                                    border="0"
                                >
                                    <tr>
                                        <td
                                            align="center"
                                            bgcolor="#ff8300"
                                            style="
                                                width: 82px;
                                                height: 82px;
                                                border: 5px solid #fff2e5;
                                                border-radius: 50%;
                                                background-color: #ff8300;
                                                color: #ffffff;
                                                font-size: 31px;
                                                font-weight: 900;
                                            "
                                        >
                                            {initiale}
                                        </td>
                                    </tr>
                                </table>

                                <h1
                                    style="
                                        margin: 25px 0 12px;
                                        color: #171717;
                                        font-size: 28px;
                                        font-weight: 900;
                                        line-height: 1.25;
                                    "
                                >
                                    Tu as un nouvel abonné !
                                </h1>

                                <p
                                    style="
                                        margin: 0;
                                        color: #67676f;
                                        font-size: 16px;
                                        line-height: 1.7;
                                    "
                                >
                                    Bonjour
                                    <strong
                                        style="
                                            color: #171717;
                                        "
                                    >
                                        {nom_createur}
                                    </strong>,
                                </p>

                                <p
                                    style="
                                        margin: 10px 0 25px;
                                        color: #67676f;
                                        font-size: 16px;
                                        line-height: 1.7;
                                    "
                                >
                                    Une nouvelle personne vient
                                    de rejoindre ta communauté
                                    AfroFans.
                                </p>

                                <!-- CARTE DE L’ABONNÉ -->

                                <table
                                    role="presentation"
                                    width="100%"
                                    cellspacing="0"
                                    cellpadding="0"
                                    border="0"
                                    style="
                                        width: 100%;
                                        border: 1px solid #eeeeee;
                                        border-radius: 18px;
                                        background-color: #fafafa;
                                    "
                                >
                                    <tr>
                                        <td
                                            style="
                                                padding: 22px;
                                            "
                                        >
                                            <table
                                                role="presentation"
                                                width="100%"
                                                cellspacing="0"
                                                cellpadding="0"
                                                border="0"
                                            >
                                                <tr>
                                                    <td
                                                        width="56"
                                                        valign="middle"
                                                    >
                                                        <table
                                                            role="presentation"
                                                            cellspacing="0"
                                                            cellpadding="0"
                                                            border="0"
                                                        >
                                                            <tr>
                                                                <td
                                                                    align="center"
                                                                    bgcolor="#1c1c1c"
                                                                    style="
                                                                        width: 52px;
                                                                        height: 52px;
                                                                        border-radius: 50%;
                                                                        background-color: #1c1c1c;
                                                                        color: #ff8300;
                                                                        font-size: 20px;
                                                                        font-weight: 900;
                                                                    "
                                                                >
                                                                    {initiale}
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </td>

                                                    <td
                                                        valign="middle"
                                                        style="
                                                            padding-left: 14px;
                                                            text-align: left;
                                                        "
                                                    >
                                                        <div
                                                            style="
                                                                color: #171717;
                                                                font-size: 17px;
                                                                font-weight: 900;
                                                            "
                                                        >
                                                            {nom_abonne}
                                                        </div>

                                                        <div
                                                            style="
                                                                margin-top: 5px;
                                                                color: #ff7900;
                                                                font-size: 14px;
                                                                font-weight: 700;
                                                            "
                                                        >
                                                            @{username_abonne}
                                                        </div>

                                                        <div
                                                            style="
                                                                margin-top: 6px;
                                                                color: #8b8b92;
                                                                font-size: 12px;
                                                            "
                                                        >
                                                            Nouvel abonné AfroFans
                                                        </div>
                                                    </td>

                                                    <td
                                                        align="right"
                                                        valign="middle"
                                                    >
                                                        <span
                                                            style="
                                                                display: inline-block;
                                                                padding: 7px 10px;
                                                                border-radius: 999px;
                                                                background-color: #fff0e1;
                                                                color: #ff7900;
                                                                font-size: 12px;
                                                                font-weight: 900;
                                                            "
                                                        >
                                                            Nouveau
                                                        </span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>

                                <!-- BOUTON -->

                                <table
                                    role="presentation"
                                    cellspacing="0"
                                    cellpadding="0"
                                    border="0"
                                    style="
                                        margin-top: 30px;
                                    "
                                >
                                    <tr>
                                        <td
                                            align="center"
                                            bgcolor="#ff7900"
                                            style="
                                                border-radius: 999px;
                                                background-color: #ff7900;
                                            "
                                        >
                                            <a
                                                href="{url_profil}"
                                                target="_blank"
                                                style="
                                                    display: inline-block;
                                                    padding: 16px 32px;
                                                    color: #ffffff;
                                                    font-size: 15px;
                                                    font-weight: 900;
                                                    text-decoration: none;
                                                "
                                            >
                                                Voir son profil&nbsp;&nbsp;→
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <p
                                    style="
                                        margin: 28px 0 0;
                                        color: #67676f;
                                        font-size: 14px;
                                        line-height: 1.7;
                                    "
                                >
                                    Continue à partager tes vidéos
                                    et à faire grandir ta communauté.
                                    Ton talent mérite d’être vu.
                                </p>
                            </td>
                        </tr>

                        <!-- PIED DE PAGE -->

                        <tr>
                            <td
                                align="center"
                                bgcolor="#f8f8fa"
                                style="
                                    padding: 27px 30px;
                                    border-top: 1px solid #eeeeee;
                                    background-color: #f8f8fa;
                                "
                            >
                                <div
                                    style="
                                        color: #1b1b1b;
                                        font-size: 14px;
                                        font-weight: 900;
                                    "
                                >
                                    Afro<span
                                        style="
                                            color: #ff7900;
                                        "
                                    >Fans</span>
                                </div>

                                <p
                                    style="
                                        margin: 8px 0 0;
                                        color: #96969e;
                                        font-size: 11px;
                                        line-height: 1.6;
                                    "
                                >
                                    Une plateforme propulsée par
                                    <strong
                                        style="
                                            color: #ff7900;
                                        "
                                    >
                                        HexaQuébec
                                    </strong>
                                </p>

                                <p
                                    style="
                                        margin: 11px 0 0;
                                        color: #b0b0b6;
                                        font-size: 10px;
                                    "
                                >
                                    Ce courriel a été envoyé
                                    automatiquement par AfroFans.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    courriel = EmailMessage(
        subject=sujet,
        body=message_html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[createur.email],
    )

    # Très important : force l’envoi du contenu en HTML.
    courriel.content_subtype = "html"

    try:
        resultat = courriel.send(
            fail_silently=False,
        )

        print(
            "Courriel HTML envoyé au créateur :",
            createur.email,
        )

        return resultat == 1

    except Exception as erreur:
        print(
            "ERREUR ENVOI COURRIEL HTML :",
            erreur,
        )

        return False





@login_required
@require_POST
def basculer_abonnement(
    request,
    username,
):
    createur = get_object_or_404(
        User.objects.select_related("profil"),
        username=username,
    )

    if createur == request.user:
        return JsonResponse(
            {
                "succes": False,
                "message": (
                    "Tu ne peux pas t’abonner "
                    "à ton propre compte."
                ),
            },
            status=400,
        )

    if createur.profil.type_compte != "createur":
        return JsonResponse(
            {
                "succes": False,
                "message": (
                    "Ce compte n’est pas "
                    "un compte créateur."
                ),
            },
            status=400,
        )

    abonnement = Abonnement.objects.filter(
        fan=request.user,
        createur=createur,
    ).first()

    if abonnement:
        abonnement.delete()

        est_abonne = False

        message = (
            "Tu es maintenant désabonné."
        )

    else:
        Abonnement.objects.create(
            fan=request.user,
            createur=createur,
        )

        est_abonne = True

        message = (
            "Tu es maintenant abonné à ce talent."
        )

        chemin_profil = reverse(
            "Afrons:profil_public",
            kwargs={
                "username": request.user.username,
            },
        )

        url_profil = request.build_absolute_uri(
            chemin_profil,
        )

        # C’est cette fonction qui envoie le design HTML.
        envoyer_courriel_nouvel_abonne(
            createur=createur,
            nouvel_abonne=request.user,
            url_profil=url_profil,
        )

    nombre_abonnes = (
        Abonnement.objects
        .filter(createur=createur)
        .count()
    )

    return JsonResponse(
        {
            "succes": True,
            "est_abonne": est_abonne,
            "nombre_abonnes": nombre_abonnes,
            "message": message,
        }
    )







# =====================================================
# AFROFANS - PORTEFEUILLE DU TALENT
# DEMANDE DE RETRAIT
# =====================================================

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET", "POST"])
def demander_retrait(request):

    # Vérifier le compte utilisateur
    profil = getattr(
        request.user,
        "profil",
        None,
    )

    if profil is None:
        return HttpResponse(
            "Aucun profil AfroFans trouvé.",
            status=403,
        )

    # Seuls les talents et organisateurs
    # peuvent accéder aux retraits.
    if profil.type_compte not in (
        "createur",
        "organisateur",
    ):
        return HttpResponse(
            "Accès réservé aux talents "
            "et organisateurs.",
            status=403,
        )

    # Protection temporaire :
    # aucun retrait réel n'est effectué
    # tant que le portefeuille et
    # le prestataire ne sont pas raccordés.

    return HttpResponse(
        "AfroFans - Portefeuille du talent. "
        "Les retraits Wave et bancaires "
        "ne sont pas encore activés. "
        "Aucun montant n'a été débité.",
        status=503,
    )





# =====================================================
# AFROFANS - CONVERTIR UN FAN EN TALENT
# =====================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET", "POST"])
def devenir_talent(request):
    """
    Permet à un utilisateur Fan de convertir
    son compte en compte Talent AfroFans.

    Le type de compte "createur" correspond
    au compte Talent dans le modèle existant.

    La conversion ne valide pas automatiquement
    une habilitation à organiser des événements.
    """

    profil = getattr(request.user, "profil", None)

    # Vérifier l'existence du profil
    if profil is None:
        return HttpResponseForbidden(
            "Aucun profil AfroFans associé à ce compte."
        )

    # Compte déjà converti
    if profil.type_compte == "createur":
        messages.info(
            request,
            "Ton compte est déjà un compte Talent."
        )

        return redirect(
            "Afrons:profil_public",
            username=request.user.username,
        )

    # Seuls les fans peuvent effectuer la conversion
    if profil.type_compte != "fan":
        return HttpResponseForbidden(
            "Ce type de compte ne peut pas être "
            "converti automatiquement en Talent."
        )

    # =============================================
    # CONFIRMER LA CONVERSION
    # =============================================

    if request.method == "POST":

        profil.type_compte = "createur"

        profil.save(
            update_fields=["type_compte"]
        )

        messages.success(
            request,
            "Félicitations ! Ton compte Fan "
            "a été converti en compte Talent AfroFans. "
            "Complète maintenant ton profil."
        )

        return redirect(
            "Afrons:modifier_profil"
        )

    # =============================================
    # PAGE DE CONFIRMATION
    # =============================================

    csrf_token = get_token(request)

    return HttpResponse(
        format_html(
            """
            <!DOCTYPE html>
            <html lang="fr">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1">

                <title>Devenir Talent - AfroFans</title>
            </head>

            <body style="
                margin:0;
                min-height:100vh;
                display:flex;
                justify-content:center;
                align-items:center;
                background:#101014;
                font-family:Arial,sans-serif;
                color:white;
            ">

                <main style="
                    max-width:470px;
                    margin:20px;
                    padding:35px;
                    border-radius:22px;
                    background:#1c1c24;
                    text-align:center;
                ">

                    <h1 style="color:#ff8500">
                        AfroFans
                    </h1>

                    <h2>
                        Devenir Talent
                    </h2>

                    <p style="
                        color:#c8c8d0;
                        line-height:1.7;
                    ">
                        Transforme ton compte Fan
                        en compte Talent pour publier
                        tes vidéos, développer ta
                        communauté et accéder aux
                        fonctionnalités destinées
                        aux créateurs.
                    </p>

                    <p style="
                        color:#c8c8d0;
                        line-height:1.6;
                    ">
                        Certaines fonctionnalités,
                        notamment la billetterie,
                        peuvent nécessiter une
                        validation supplémentaire.
                    </p>

                    <form method="post">

                        <input
                            type="hidden"
                            name="csrfmiddlewaretoken"
                            value="{}"
                        >

                        <button type="submit" style="
                            width:100%;
                            padding:15px;
                            border:0;
                            border-radius:12px;
                            background:#ff8500;
                            color:white;
                            font-size:16px;
                            font-weight:bold;
                            cursor:pointer;
                        ">
                            Confirmer ma conversion
                        </button>

                    </form>

                </main>

            </body>
            </html>
            """,
            csrf_token,
        )
    )





# =====================================================
# AFROFANS - PARAMÈTRES DU COMPTE
# DÉSACTIVATION / SUPPRESSION
# =====================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET", "POST"])
def action_compte(request):
    """
    Paramètres de désactivation et suppression.

    Protection temporaire :
    aucune modification du compte n'est effectuée
    avant la vérification du portefeuille,
    des retraits et des obligations financières.
    """

    if request.method == "POST":
        messages.warning(
            request,
            "La désactivation et la suppression "
            "du compte ne sont pas encore activées. "
            "Ton compte et ton argent restent inchangés."
        )

        return redirect(
            "Afrons:modifier_profil"
        )

    return HttpResponse(
        "<h1>Paramètres du compte AfroFans</h1>"
        "<p>La désactivation et la suppression "
        "seront disponibles après intégration "
        "des vérifications financières.</p>",
        status=200,
    )




import io
import secrets

from datetime import timedelta
from hashlib import sha256
from decimal import Decimal

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from django.db import transaction, IntegrityError
from django.db.models import Q

from django.http import (
    HttpResponse,
    HttpResponseForbidden,
)

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.urls import reverse
from django.utils import timezone

from django.views.decorators.cache import never_cache
from django.views.decorators.http import (
    require_POST,
    require_GET,
)

from .models import (
    Evenement,
    BilletEvenement,
    PaiementFraisEvenement,
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

from .forms_billetterie import (
    EvenementForm,
    AchatBilletForm,
    ControleurEvenementForm,
)

from .services_billetterie import (
    DUREE_RESERVATION,
    capacite_restante,
)


# =====================================================
# 1. AUTORISATIONS
# =====================================================

STATUTS_PUBLICS = ("publie", "ouvert")


# ============================================================
# AFROFANS — VÉRIFICATION TALENT / ORGANISATEUR
# Reconnaissance de la certification par l'administrateur
# ============================================================

def vendeur_verifie(user):

    # 1. L'utilisateur doit être connecté.
    if not user.is_authenticated:
        return False

    # 2. Récupérer son profil AfroFans.
    profil = getattr(user, "profil", None)

    if profil is None:
        return False

    # 3. Seuls les Talents et Organisateurs sont autorisés.
    if profil.type_compte not in (
        "createur",
        "organisateur",
    ):
        return False

    # 4. Certification accordée directement par l'admin.
    # Aucune demande de vérification supplémentaire requise.
    if profil.est_certifie:
        return True

    # 5. Vérification par le système de billetterie.
    # Le compte doit posséder une habilitation approuvée.
    return HabilitationBilletterie.objects.filter(
        user=user,
        statut="verifie",
    ).exists()


def evenement_du_vendeur(request, evenement_id):
    return get_object_or_404(
        Evenement,
        pk=evenement_id,
        createur=request.user,
    )


# =====================================================
# 2. CRÉER UN ÉVÉNEMENT
# =====================================================

@login_required
@transaction.atomic
def creer_evenement(request):

    if not vendeur_verifie(request.user):
        messages.error(
            request,
            "Seuls les talents et organisateurs "
            "vérifiés peuvent créer des événements.",
        )

        return redirect("Afrons:flux")

    formulaire = EvenementForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and formulaire.is_valid():

        if request.POST.get("accept_conditions") != "oui":
            formulaire.add_error(
                None,
                "Tu dois accepter les conditions.",
            )

        else:
            evenement = formulaire.save(commit=False)

            evenement.createur = request.user
            evenement.statut = "paiement_attente"

            evenement.save()
            formulaire.save_m2m()

            paiement = PaiementFraisEvenement.objects.create(
                evenement=evenement,
                createur=request.user,
                devise_paiement="XOF",
                taux_conversion=Decimal("1"),
            )

            messages.success(
                request,
                "Événement créé. Paie les frais de "
                "billetterie avant sa validation.",
            )

            return redirect(
                "Afrons:payer_frais_evenement",
                paiement_id=paiement.pk,
            )

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,
            "titre": "Créer un événement",
        },
    )


# =====================================================
# 3. MODIFIER UN ÉVÉNEMENT
# =====================================================

@login_required
@transaction.atomic
def modifier_evenement(request, evenement_id):

    evenement = get_object_or_404(
        Evenement.objects.select_for_update(),
        pk=evenement_id,
        createur=request.user,
    )

    if not vendeur_verifie(request.user):
        return HttpResponseForbidden(
            "Compte non vérifié."
        )

    if evenement.statut in (
        "ouvert",
        "termine",
        "annule",
    ):
        messages.error(
            request,
            "Cet événement ne peut plus être modifié.",
        )

        return redirect(evenement)

    if BilletEvenement.objects.filter(
        evenement=evenement,
        statut="paye",
    ).exists():
        messages.error(
            request,
            "Des billets ont déjà été vendus. "
            "Contacte AfroFans pour modifier "
            "l'événement.",
        )

        return redirect(evenement)

    ancienne_capacite = evenement.nombre_places
    ancien_statut = evenement.statut

    formulaire = EvenementForm(
        request.POST or None,
        request.FILES or None,
        instance=evenement,
    )

    if request.method == "POST" and formulaire.is_valid():

        if request.POST.get("accept_conditions") != "oui":
            formulaire.add_error(
                None,
                "Accepte les conditions pour continuer.",
            )

        else:
            evenement = formulaire.save(commit=False)

            capacite_modifiee = (
                evenement.nombre_places != ancienne_capacite
            )

            if capacite_modifiee:
                evenement.frais_billetterie_payes = False
                evenement.frais_payes_le = None
                evenement.statut = "paiement_attente"

            elif ancien_statut == "paiement_attente":
                evenement.statut = "paiement_attente"

            else:
                evenement.statut = "en_attente"

            evenement.save()
            formulaire.save_m2m()

            if capacite_modifiee:

                paiement = PaiementFraisEvenement.objects.create(
                    evenement=evenement,
                    createur=request.user,
                    devise_paiement="XOF",
                    taux_conversion=Decimal("1"),
                )

                return redirect(
                    "Afrons:payer_frais_evenement",
                    paiement_id=paiement.pk,
                )

            messages.success(
                request,
                "Modifications enregistrées et "
                "envoyées pour validation.",
            )

            return redirect(evenement)

    return render(
        request,
        "Afrons/formulaire_evenement.html",
        {
            "formulaire": formulaire,
            "titre": "Modifier l'événement",
            "evenement": evenement,
        },
    )


# =====================================================
# 4. DÉTAIL PUBLIC DE L'ÉVÉNEMENT
# =====================================================

def detail_evenement(request, evenement_id):

    filtre = Q(
        pk=evenement_id,
        statut__in=STATUTS_PUBLICS,
    )

    if request.user.is_authenticated:
        filtre |= Q(
            pk=evenement_id,
            createur=request.user,
        )

    evenement = get_object_or_404(
        Evenement.objects.select_related(
            "createur",
            "createur__profil",
        ),
        filtre,
    )

    formulaire = AchatBilletForm(
        evenement=evenement,
    )

    proprietaire = (
        request.user.is_authenticated
        and request.user.pk == evenement.createur_id
    )

    return render(
        request,
        "Afrons/detail_evenement.html",
        {
            "evenement": evenement,
            "formulaire": formulaire,
            "est_proprietaire": proprietaire,
            "places_disponibles": (
                capacite_restante(evenement)
                if evenement.statut in STATUTS_PUBLICS
                else 0
            ),
        },
    )


# =====================================================
# 5. ACHETER UN BILLET
# =====================================================

@login_required
@require_POST
@transaction.atomic
def acheter_billet(request, evenement_id):

    evenement = get_object_or_404(
        Evenement.objects.select_for_update(),
        pk=evenement_id,
        statut__in=STATUTS_PUBLICS,
    )

    if request.user.pk == evenement.createur_id:
        messages.error(
            request,
            "Tu ne peux pas acheter ton propre billet.",
        )

        return redirect(evenement)

    profil = getattr(request.user, "profil", None)

    if not profil or profil.type_compte != "fan":
        messages.error(
            request,
            "Seuls les comptes Fan peuvent "
            "acheter des billets.",
        )

        return redirect(evenement)

    formulaire = AchatBilletForm(
        request.POST,
        evenement=evenement,
    )

    formulaire.instance.evenement = evenement
    formulaire.instance.acheteur = request.user

    if formulaire.is_valid():

        billet = formulaire.save(commit=False)

        billet.evenement = evenement
        billet.acheteur = request.user
        billet.statut = "en_attente"

        if billet.quantite > capacite_restante(evenement):
            formulaire.add_error(
                "quantite",
                "Nombre de places insuffisant.",
            )

        else:
            billet.save()

            ReservationExpiration.objects.create(
                billet=billet,
                expire_le=(
                    timezone.now()
                    + DUREE_RESERVATION
                ),
            )

            messages.success(
                request,
                "Réservation enregistrée pour "
                "10 minutes. Termine le paiement "
                "pour obtenir tes QR codes.",
            )

            return redirect(
                "Afrons:confirmation_billet",
                code_billet=billet.code_billet,
            )

    return render(
        request,
        "Afrons/detail_evenement.html",
        {
            "evenement": evenement,
            "formulaire": formulaire,
            "places_disponibles": (
                capacite_restante(evenement)
            ),
        },
        status=400,
    )


# =====================================================
# 6. CONFIRMATION ET MES BILLETS
# =====================================================

@login_required
@never_cache
def confirmation_billet(request, code_billet):

    billet = get_object_or_404(
        BilletEvenement.objects.select_related(
            "evenement"
        ),
        code_billet=code_billet,
        acheteur=request.user,
    )

    billets_qr = []

    if billet.statut == "paye":
        billets_qr = list(
            BilletAcces.objects.filter(
                reservation=billet
            ).order_by("cree_le", "pk")
        )

    blocage = ReservationExpiration.objects.filter(
        billet=billet
    ).first()

    return render(
        request,
        "Afrons/confirmation_billet.html",
        {
            "billet": billet,
            "billets_qr": billets_qr,
            "blocage": blocage,
        },
    )


# =====================================================
# 7. OUVRIR UN ÉVÉNEMENT
# =====================================================

@login_required
@require_POST
@transaction.atomic
def ouvrir_evenement(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    if not vendeur_verifie(request.user):
        return HttpResponseForbidden(
            "Compte non vérifié."
        )

    evenement = (
        Evenement.objects
        .select_for_update()
        .get(pk=evenement.pk)
    )

    if evenement.statut != "publie":
        messages.error(
            request,
            "L'événement doit d'abord être publié.",
        )

        return redirect(
            "Afrons:tableau_presence",
            evenement_id=evenement.pk,
        )

    if not evenement.frais_billetterie_payes:
        messages.error(
            request,
            "Les frais ne sont pas encore payés.",
        )

        return redirect(
            "Afrons:tableau_presence",
            evenement_id=evenement.pk,
        )

    # Un code unique est créé uniquement
    # pour cet événement.

    CodeAccesEvenement.objects.get_or_create(
        evenement=evenement
    )

    evenement.statut = "ouvert"
    evenement.save(update_fields=["statut"])

    messages.success(
        request,
        "Événement ouvert. Tu peux communiquer "
        "le code unique aux contrôleurs.",
    )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=evenement.pk,
    )


# =====================================================
# 8. TERMINER UN ÉVÉNEMENT
# =====================================================

@login_required
@require_POST
@transaction.atomic
def terminer_evenement(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    evenement = (
        Evenement.objects
        .select_for_update()
        .get(pk=evenement.pk)
    )

    if evenement.statut == "ouvert":

        evenement.statut = "termine"
        evenement.save(update_fields=["statut"])

        messages.success(
            request,
            "Événement terminé. Les billets "
            "non utilisés sont désormais "
            "classés comme absents.",
        )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=evenement.pk,
    )


# =====================================================
# 9. ENVOYER UNE INVITATION PAR COURRIEL
# =====================================================

def envoyer_invitation_controleur(request, controleur):

    jeton = secrets.token_urlsafe(32)

    empreinte = sha256(
        jeton.encode("utf-8")
    ).hexdigest()

    invitation, _ = (
        InvitationControleur.objects
        .update_or_create(
            controleur=controleur,
            defaults={
                "empreinte_jeton": empreinte,
                "expire_le": (
                    timezone.now()
                    + timedelta(hours=48)
                ),
                "utilise_le": None,
            },
        )
    )

    lien = request.build_absolute_uri(
        reverse(
            "Afrons:invitation_controleur",
            args=[controleur.pk, jeton],
        )
    )

    contenu = (
        f"Bonjour {controleur.prenom} "
        f"{controleur.nom},\n\n"

        "Tu as été invité à devenir contrôleur "
        "de billets pour un événement AfroFans.\n\n"

        f"Événement : "
        f"{controleur.evenement.titre}\n\n"

        f"Lien d'accès personnel :\n{lien}\n\n"

        "Ce lien est valable pendant 48 heures.\n\n"

        "Le talent ou l'organisateur te "
        "communiquera séparément le code "
        "unique de son événement.\n\n"

        "Clique sur le lien, entre le code "
        "de l'événement, puis utilise le "
        "scanner pour valider les billets.\n\n"

        "Ne partage pas cette invitation.\n\n"

        "L'équipe AfroFans"
    )

    send_mail(
        subject="AfroFans - Invitation contrôleur",
        message=contenu,
        from_email=None,
        recipient_list=[controleur.email],
        fail_silently=False,
    )

    return invitation


# =====================================================
# 10. CRÉER UN CONTRÔLEUR
# =====================================================

@login_required
def creer_controleur(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    if not vendeur_verifie(request.user):
        return HttpResponseForbidden(
            "Compte vendeur non vérifié."
        )

    if evenement.statut not in ("publie", "ouvert"):
        return HttpResponseForbidden(
            "L'événement n'est pas encore "
            "autorisé à recevoir des contrôleurs."
        )

    formulaire = ControleurEvenementForm(
        request.POST or None
    )

    if request.method == "POST" and formulaire.is_valid():

        controleur = formulaire.save(commit=False)
        controleur.evenement = evenement

        if ControleurEvenement.objects.filter(
            evenement=evenement,
            email=controleur.email,
        ).exists():
            formulaire.add_error(
                "email",
                "Ce contrôleur existe déjà "
                "pour cet événement.",
            )

        else:
            try:
                controleur.save()

            except IntegrityError:
                formulaire.add_error(
                    "email",
                    "Adresse déjà utilisée.",
                )

            else:
                try:
                    envoyer_invitation_controleur(
                        request,
                        controleur,
                    )

                except Exception:
                    messages.warning(
                        request,
                        "Contrôleur enregistré, mais "
                        "le courriel n'a pas été envoyé. "
                        "Vérifie le SMTP et renvoie "
                        "l'invitation.",
                    )

                else:
                    messages.success(
                        request,
                        "Contrôleur créé. Invitation "
                        "envoyée à son courriel.",
                    )

                return redirect(
                    "Afrons:tableau_presence",
                    evenement_id=evenement.pk,
                )

    return render(
        request,
        "Afrons/formulaire_controleur.html",
        {
            "evenement": evenement,
            "formulaire": formulaire,
        },
    )


# =====================================================
# 11. RENVOYER UNE INVITATION
# =====================================================

@login_required
@require_POST
def renvoyer_invitation(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        evenement__createur=request.user,
    )

    if not controleur.actif:
        return HttpResponseForbidden(
            "Contrôleur désactivé."
        )

    try:
        envoyer_invitation_controleur(
            request,
            controleur,
        )

    except Exception:
        messages.error(
            request,
            "Impossible d'envoyer le courriel.",
        )

    else:
        messages.success(
            request,
            "Nouvelle invitation envoyée.",
        )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=controleur.evenement_id,
    )


# =====================================================
# 12. DÉSACTIVER UN CONTRÔLEUR
# =====================================================

@login_required
@require_POST
def desactiver_controleur(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement,
        pk=controleur_id,
        evenement__createur=request.user,
    )

    controleur.actif = False
    controleur.save(update_fields=["actif"])

    messages.success(
        request,
        "Accès du contrôleur désactivé.",
    )

    return redirect(
        "Afrons:tableau_presence",
        evenement_id=controleur.evenement_id,
    )


# =====================================================
# 13. SESSION PRIVÉE DU CONTRÔLEUR
# =====================================================

def controleur_connecte(request, controleur):

    session = request.session.get(
        f"af_controle_{controleur.pk}",
        {},
    )

    return bool(
        controleur.actif
        and controleur.evenement.statut == "ouvert"
        and session.get("ok")
        and session.get("expire", 0)
        > timezone.now().timestamp()
    )


# =====================================================
# 14. LE CONTRÔLEUR CLIQUE SUR SON LIEN
# =====================================================

@never_cache
def invitation_controleur(
    request,
    controleur_id,
    jeton,
):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        actif=True,
    )

    invitation = get_object_or_404(
        InvitationControleur,
        controleur=controleur,
    )

    if not invitation.jeton_est_valide(jeton):
        return HttpResponseForbidden(
            "Invitation invalide, déjà utilisée "
            "ou expirée. Demande un nouveau lien."
        )

    request.session.cycle_key()

    request.session[
        f"af_invite_{controleur.pk}"
    ] = {
        "empreinte": invitation.empreinte_jeton,
        "expire": invitation.expire_le.timestamp(),
    }

    return redirect(
        "Afrons:code_controleur",
        controleur_id=controleur.pk,
    )


# =====================================================
# 15. SAISIE DU CODE UNIQUE DE L'ÉVÉNEMENT
# =====================================================

@never_cache
def code_controleur(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
        actif=True,
    )

    if controleur.evenement.statut != "ouvert":
        return HttpResponseForbidden(
            "Cet événement n'est pas encore ouvert."
        )

    if controleur_connecte(request, controleur):
        return redirect(
            "Afrons:scanner_evenement",
            controleur_id=controleur.pk,
        )

    donnees = request.session.get(
        f"af_invite_{controleur.pk}"
    )

    invitation = InvitationControleur.objects.filter(
        controleur=controleur
    ).first()

    valide = (
        isinstance(donnees, dict)
        and invitation is not None
        and invitation.utilise_le is None
        and invitation.expire_le > timezone.now()
        and donnees.get("expire", 0)
        > timezone.now().timestamp()
        and secrets.compare_digest(
            donnees.get("empreinte", ""),
            invitation.empreinte_jeton,
        )
    )

    if not valide:
        return HttpResponseForbidden(
            "Accès refusé. Utilise le lien "
            "d'invitation reçu par courriel."
        )

    if request.method == "POST":

        maintenant = timezone.now().timestamp()

        cle_essais = f"af_essais_{controleur.pk}"

        essais = request.session.get(
            cle_essais,
            [],
        )

        essais = [
            instant
            for instant in essais
            if maintenant - instant < 900
        ]

        if len(essais) >= 5:
            return HttpResponseForbidden(
                "Trop de tentatives. Réessaie "
                "dans 15 minutes."
            )

        essais.append(maintenant)
        request.session[cle_essais] = essais

        code_saisi = (
            request.POST.get(
                "code_evenement",
                "",
            ).strip().upper()
        )

        code_acces = CodeAccesEvenement.objects.filter(
            evenement=controleur.evenement
        ).first()

        code_valide = (
            code_acces is not None
            and secrets.compare_digest(
                code_saisi,
                code_acces.code,
            )
        )

        if code_valide:

            with transaction.atomic():
                modifie = InvitationControleur.objects.filter(
                    pk=invitation.pk,
                    empreinte_jeton=invitation.empreinte_jeton,
                    utilise_le__isnull=True,
                    expire_le__gt=timezone.now(),
                ).update(
                    utilise_le=timezone.now()
                )

            if modifie != 1:
                return HttpResponseForbidden(
                    "Invitation déjà utilisée ou expirée."
                )

            request.session[
                f"af_controle_{controleur.pk}"
            ] = {
                "ok": True,
                "expire": maintenant + 8 * 3600,
            }

            request.session.pop(
                f"af_invite_{controleur.pk}",
                None,
            )

            request.session.pop(
                cle_essais,
                None,
            )

            return redirect(
                "Afrons:scanner_evenement",
                controleur_id=controleur.pk,
            )

        messages.error(
            request,
            "Code événement incorrect.",
        )

    return render(
        request,
        "Afrons/code_controleur.html",
        {
            "controleur": controleur,
        },
    )


# =====================================================
# 16. SCANNER LES BILLETS QR
# =====================================================

@never_cache
def scanner_evenement(request, controleur_id):

    controleur = get_object_or_404(
        ControleurEvenement.objects.select_related(
            "evenement"
        ),
        pk=controleur_id,
    )

    if not controleur_connecte(request, controleur):
        return HttpResponseForbidden(
            "Session expirée ou accès révoqué."
        )

    resultat = None
    billet = None

    if request.method == "POST":

        jeton = request.POST.get(
            "ticket_token",
            "",
        ).strip()

        if not jeton or len(jeton) > 1000:
            resultat = "QR code invalide."

        else:
            try:
                contenu = signing.loads(
                    jeton,
                    salt="afrofans-ticket-v1",
                )

                billet_id = contenu["ticket_id"]
                evenement_qr = contenu["event_id"]

                if (
                    evenement_qr
                    != controleur.evenement_id
                ):
                    resultat = (
                        "Billet d'un autre événement."
                    )

                else:
                    with transaction.atomic():

                        billet = (
                            BilletAcces.objects
                            .select_for_update()
                            .select_related("reservation")
                            .filter(pk=billet_id)
                            .first()
                        )

                        if billet is None:
                            resultat = (
                                "Billet inexistant."
                            )

                        else:
                            if (
                                billet.evenement_id
                                != controleur.evenement_id
                            ):
                                resultat = (
                                    "Billet d'un autre événement."
                                )
                                code_resultat = "autre_evenement"

                            elif (
                                billet.reservation.statut
                                != "paye"
                                or billet.statut == "annule"
                            ):
                                resultat = (
                                    "Billet non valide ou annulé."
                                )
                                code_resultat = "annule"

                            elif billet.statut == "utilise":
                                resultat = (
                                    "Billet déjà utilisé."
                                )
                                code_resultat = "deja_utilise"

                            elif (
                                not billet.prenom_participant
                                or not billet.nom_participant
                            ):
                                resultat = (
                                    "Identité du participant "
                                    "non renseignée."
                                )
                                code_resultat = "incomplet"

                            else:
                                instant = timezone.now()

                                modifie = (
                                    BilletAcces.objects
                                    .filter(
                                        pk=billet.pk,
                                        statut="actif",
                                    )
                                    .update(
                                        statut="utilise",
                                        utilise_le=instant,
                                        controleur_entree=controleur,
                                    )
                                )

                                if modifie:
                                    billet.statut = "utilise"
                                    billet.utilise_le = instant
                                    resultat = "ENTRÉE VALIDÉE"
                                    code_resultat = "valide"

                                else:
                                    resultat = (
                                        "Billet déjà utilisé."
                                    )
                                    code_resultat = "deja_utilise"

                            HistoriqueScan.objects.create(
                                billet=billet,
                                controleur=controleur,
                                resultat=code_resultat,
                            )

            except (
                signing.BadSignature,
                ValueError,
                KeyError,
                TypeError,
                ValidationError,
            ):
                resultat = "QR code inconnu ou falsifié."

    return render(
        request,
        "Afrons/scanner_evenement.html",
        {
            "controleur": controleur,
            "resultat": resultat,
            "billet_scanne": billet,
        },
    )


# =====================================================
# 17. TABLEAU DE PRÉSENCE DU TALENT
# =====================================================

@login_required
@never_cache
def tableau_presence(request, evenement_id):

    evenement = evenement_du_vendeur(
        request,
        evenement_id,
    )

    billets = list(
        BilletAcces.objects.filter(
            evenement=evenement,
            reservation__statut="paye",
        ).select_related(
            "reservation__acheteur",
            "controleur_entree",
        ).order_by(
            "nom_participant",
            "prenom_participant",
        )
    )

    presents = sum(
        billet.statut == "utilise"
        for billet in billets
    )

    non_entres = [
        billet
        for billet in billets
        if billet.statut == "actif"
    ]

    controleurs = ControleurEvenement.objects.filter(
        evenement=evenement
    )

    code_acces = CodeAccesEvenement.objects.filter(
        evenement=evenement
    ).first()

    return render(
        request,
        "Afrons/tableau_presence.html",
        {
            "evenement": evenement,
            "billets": billets,
            "presents": presents,
            "non_entres": non_entres,
            "nombre_total": len(billets),
            "controleurs": controleurs,
            "code_acces": code_acces,
            "cloture": evenement.statut == "termine",
        },
    )


# =====================================================
# 18. CRÉER L'IMAGE QR DU BILLET
# =====================================================

@login_required
@require_GET
@never_cache
def image_qr_billet(request, billet_id):

    billet = get_object_or_404(
        BilletAcces.objects.select_related(
            "reservation",
        ),
        pk=billet_id,
        reservation__acheteur=request.user,
        reservation__statut="paye",
    )

    if billet.statut == "annule":
        return HttpResponseForbidden(
            "Billet annulé."
        )

    if (
        not billet.prenom_participant
        or not billet.nom_participant
    ):
        return HttpResponseForbidden(
            "Renseigne le nom et le prénom "
            "du participant."
        )

    image = qrcode.make(
        billet.jeton_qr()
    )

    tampon = io.BytesIO()
    image.save(tampon, format="PNG")

    reponse = HttpResponse(
        tampon.getvalue(),
        content_type="image/png",
    )

    reponse["Cache-Control"] = (
        "no-store, private"
    )

    return reponse


# =====================================================
# 19. NOMMER CHAQUE PARTICIPANT
# =====================================================

@login_required
@require_POST
@transaction.atomic
def nommer_participant(request, billet_id):

    billet = get_object_or_404(
        BilletAcces.objects
        .select_for_update()
        .select_related(
            "reservation",
            "evenement",
        ),
        pk=billet_id,
        reservation__acheteur=request.user,
        reservation__statut="paye",
        statut="actif",
    )

    if billet.evenement.statut in (
        "termine",
        "annule",
    ):
        return HttpResponseForbidden(
            "Événement terminé ou annulé."
        )

    prenom = request.POST.get(
        "prenom", ""
    ).strip()

    nom = request.POST.get(
        "nom", ""
    ).strip()

    if (
        not prenom
        or not nom
        or len(prenom) > 100
        or len(nom) > 100
    ):
        messages.error(
            request,
            "Indique le nom et le prénom "
            "(100 caractères maximum).",
        )

    else:
        billet.prenom_participant = prenom
        billet.nom_participant = nom

        billet.save(
            update_fields=[
                "prenom_participant",
                "nom_participant",
            ]
        )

        messages.success(
            request,
            "Participant enregistré.",
        )

    return redirect(
        "Afrons:confirmation_billet",
        code_billet=billet.reservation.code_billet,
    )



import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect

from .models import DemandeVerificationTalent
from .forms import FormulaireVerificationTalent


# ============================================================
# AFROFANS — VÉRIFICATION OFFICIELLE DES TALENTS
# ============================================================

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# STATUTS BLOQUANT UNE NOUVELLE DEMANDE
# ------------------------------------------------------------

STATUTS_DEMANDE_ACTIVE = (
    "paiement_attente",
    "en_attente",
    "en_cours",
    "approuvee",
)


# ------------------------------------------------------------
# CORRESPONDANCE FORMULAIRE / MODÈLE
# ------------------------------------------------------------

CHAMPS_ERREURS_MODELE = {
    "nom": "nom",
    "prenom": "prenom",
    "date_naissance": "date_naissance",
    "pays": "pays",
    "email": "email",
    "telephone": "telephone",
    "nom_artistique": "nom_scene",
    "categorie_talent": "categorie",
    "description_activite": "description",
    "lien_public": "lien_public",
    "type_document": "type_piece",
    "document_recto": "piece_recto",
    "document_verso": "piece_verso",
    "photo_identite": "photo_identite",
    "consentement_verification": "declaration",
}


# ============================================================
# VUE — FORMULAIRE DE VÉRIFICATION TALENT
# ============================================================

@login_required
def formulaire_verification_talent(request):

    template = "Afrons/formulaire_verification_talent.html"

    # --------------------------------------------------------
    # 1. RÉCUPÉRER LE PROFIL
    # --------------------------------------------------------

    profil = getattr(request.user, "profil", None)

    if profil is None:

        messages.error(
            request,
            "Votre profil AfroFans est introuvable."
        )

        return redirect("Afrons:flux")

    # --------------------------------------------------------
    # 2. ACCÈS RÉSERVÉ AUX TALENTS
    # --------------------------------------------------------

    if profil.type_compte != "createur":

        messages.error(
            request,
            "La vérification officielle est exclusivement "
            "réservée aux comptes Talent."
        )

        return redirect("Afrons:flux")

    # --------------------------------------------------------
    # 3. COMPTE DÉJÀ CERTIFIÉ
    # --------------------------------------------------------

    if profil.est_certifie:

        messages.success(
            request,
            "Votre compte Talent est déjà vérifié."
        )

        return redirect("Afrons:flux")

    # --------------------------------------------------------
    # 4. RECHERCHER UNE DEMANDE EXISTANTE
    # --------------------------------------------------------

    demande_existante = (
        DemandeVerificationTalent.objects
        .filter(
            talent=profil,
            statut__in=STATUTS_DEMANDE_ACTIVE,
        )
        .order_by("-date_soumission")
        .first()
    )

    if demande_existante:

        return render(
            request,
            template,
            {
                "profil": profil,
                "demande_existante": demande_existante,
                "formulaire": None,
            }
        )

    # --------------------------------------------------------
    # 5. INFORMATIONS INITIALES
    # --------------------------------------------------------

    donnees_initiales = {
        "prenom": request.user.first_name or "",
        "nom": request.user.last_name or "",
        "nom_scene": (
            getattr(profil, "nom_scene", "") or ""
        ),
        "pays": (
            getattr(profil, "pays", "") or ""
        ),
        "email": request.user.email or "",
        "telephone": (
            getattr(profil, "numero_telephone", "") or ""
        ),
    }

    # --------------------------------------------------------
    # 6. INITIALISER LE FORMULAIRE
    # --------------------------------------------------------

    if request.method == "POST":

        formulaire = FormulaireVerificationTalent(
            request.POST,
            request.FILES,
        )

    else:

        formulaire = FormulaireVerificationTalent(
            initial=donnees_initiales
        )

    # --------------------------------------------------------
    # 7. TRAITEMENT DE LA SOUMISSION
    # --------------------------------------------------------

    if request.method == "POST":

        if formulaire.is_valid():

            donnees = formulaire.cleaned_data

            # ------------------------------------------------
            # 8. VÉRIFIER LE CONSENTEMENT
            # ------------------------------------------------

            if not donnees.get("declaration"):

                formulaire.add_error(
                    "declaration",
                    "Vous devez accepter la déclaration "
                    "avant de soumettre votre dossier."
                )

            else:

                try:

                    # ----------------------------------------
                    # 9. TRANSACTION
                    # ----------------------------------------

                    with transaction.atomic():

                        # Verrouiller le profil.

                        profil_verrouille = (
                            type(profil).objects
                            .select_for_update()
                            .get(pk=profil.pk)
                        )

                        # ------------------------------------
                        # 10. REVÉRIFIER LE TYPE DE COMPTE
                        # ------------------------------------

                        if (
                            profil_verrouille.type_compte
                            != "createur"
                        ):

                            messages.error(
                                request,
                                "Votre compte n'est pas "
                                "admissible à la vérification."
                            )

                            return redirect("Afrons:flux")

                        # ------------------------------------
                        # 11. COMPTE DÉJÀ CERTIFIÉ
                        # ------------------------------------

                        if profil_verrouille.est_certifie:

                            messages.info(
                                request,
                                "Votre compte Talent "
                                "est déjà vérifié."
                            )

                            return redirect("Afrons:flux")

                        # ------------------------------------
                        # 12. EMPÊCHER LES DOUBLONS
                        # ------------------------------------

                        demande_deja_presente = (
                            DemandeVerificationTalent.objects
                            .filter(
                                talent=profil_verrouille,
                                statut__in=STATUTS_DEMANDE_ACTIVE,
                            )
                            .exists()
                        )

                        if demande_deja_presente:

                            messages.warning(
                                request,
                                "Vous avez déjà une demande "
                                "de vérification en cours."
                            )

                            return redirect(
                                "Afrons:formulaire_verification_talent"
                            )

                        # ------------------------------------
                        # 13. TYPE DE DOCUMENT
                        # ------------------------------------

                        type_piece = donnees["type_piece"]

                        if type_piece == "permis":
                            type_piece = "permis_conduire"

                        # ------------------------------------
                        # 14. CRÉATION DU DOSSIER
                        # ------------------------------------

                        demande = DemandeVerificationTalent(

                            talent=profil_verrouille,

                            # INFORMATIONS PERSONNELLES

                            nom=donnees["nom"],

                            prenom=donnees["prenom"],

                            date_naissance=donnees[
                                "date_naissance"
                            ],

                            pays=donnees["pays"],

                            # CONTACT

                            email=donnees["email"],

                            telephone=donnees["telephone"],

                            # IDENTITÉ ARTISTIQUE

                            nom_artistique=(
                                donnees.get("nom_scene") or ""
                            ),

                            categorie_talent=donnees[
                                "categorie"
                            ],

                            description_activite=(
                                donnees.get("description") or ""
                            ),

                            # LIEN PUBLIC

                            lien_public=(
                                donnees.get("lien_public") or ""
                            ),

                            # DOCUMENT D'IDENTITÉ

                            type_document=type_piece,

                            document_recto=donnees[
                                "piece_recto"
                            ],

                            document_verso=donnees.get(
                                "piece_verso"
                            ),

                            # PHOTO D'IDENTITÉ

                            photo_identite=donnees[
                                "photo_identite"
                            ],

                            # CONSENTEMENT

                            consentement_verification=True,

                            # STATUT INITIAL

                            statut="paiement_attente",
                        )

                        # ------------------------------------
                        # 15. VALIDER LE MODÈLE
                        # ------------------------------------

                        demande.full_clean()

                        # ------------------------------------
                        # 16. ENREGISTRER LE DOSSIER
                        # ------------------------------------

                        demande.save()

                    # ----------------------------------------
                    # 17. ENREGISTREMENT RÉUSSI
                    # ----------------------------------------

                    messages.success(
                        request,
                        "Votre dossier de vérification "
                        "a été enregistré avec succès. "
                        "Le paiement des frais de vérification "
                        "reste à effectuer."
                    )

                    return redirect(
                        "Afrons:formulaire_verification_talent"
                    )

                # --------------------------------------------
                # 18. ERREURS DE VALIDATION DU MODÈLE
                # --------------------------------------------

                except ValidationError as erreur:

                    logger.warning(
                        "Validation du dossier Talent échouée. "
                        "Utilisateur ID=%s. Champs=%s",
                        request.user.pk,
                        (
                            list(erreur.message_dict.keys())
                            if hasattr(erreur, "message_dict")
                            else ["__all__"]
                        ),
                    )

                    if hasattr(erreur, "message_dict"):

                        for champ_modele, erreurs in (
                            erreur.message_dict.items()
                        ):

                            champ_formulaire = (
                                CHAMPS_ERREURS_MODELE.get(
                                    champ_modele
                                )
                            )

                            if (
                                champ_formulaire
                                and champ_formulaire
                                in formulaire.fields
                            ):

                                for message_erreur in erreurs:

                                    formulaire.add_error(
                                        champ_formulaire,
                                        message_erreur
                                    )

                            else:

                                formulaire.add_error(
                                    None,
                                    "Le dossier contient une "
                                    "information invalide."
                                )

                    else:

                        formulaire.add_error(
                            None,
                            "Les informations fournies "
                            "ne sont pas valides."
                        )

                    messages.error(
                        request,
                        "Certaines informations du dossier "
                        "sont invalides. Veuillez vérifier "
                        "les champs indiqués."
                    )

                # --------------------------------------------
                # 19. ERREURS TECHNIQUES
                # --------------------------------------------

                except Exception:

                    logger.exception(
                        "Erreur d'enregistrement du dossier "
                        "de vérification Talent. "
                        "Utilisateur ID=%s",
                        request.user.pk
                    )

                    messages.error(
                        request,
                        "Une erreur technique est survenue "
                        "pendant l'enregistrement de votre "
                        "dossier. Veuillez réessayer."
                    )

        # ----------------------------------------------------
        # 20. FORMULAIRE INVALIDE
        # ----------------------------------------------------

        else:

            logger.warning(
                "Formulaire Talent invalide. "
                "Utilisateur ID=%s. Champs=%s",
                request.user.pk,
                list(formulaire.errors.keys())
            )

            messages.error(
                request,
                "Le formulaire contient des erreurs. "
                "Veuillez vérifier les champs indiqués."
            )

    # --------------------------------------------------------
    # 21. AFFICHAGE DU FORMULAIRE
    # --------------------------------------------------------

    return render(
        request,
        template,
        {
            "profil": profil,
            "formulaire": formulaire,
            "demande_existante": None,
        }
    )





import logging

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import DemandeVerificationTalent


logger = logging.getLogger(__name__)


# ============================================================
# AFROFANS — PAIEMENT VÉRIFICATION TALENT
# ============================================================

@login_required
@require_POST
def payer_verification_talent(request, identifiant):

    profil = getattr(request.user, "profil", None)

    if profil is None or profil.type_compte != "createur":
        messages.error(
            request,
            "Cette opération est réservée aux Talents."
        )
        return redirect("Afrons:flux")

    # Récupérer uniquement le dossier du Talent connecté.

    demande = get_object_or_404(
        DemandeVerificationTalent,
        identifiant=identifiant,
        talent=profil,
    )

    if demande.statut != "paiement_attente":
        messages.warning(
            request,
            "Ce dossier n'est plus en attente de paiement."
        )
        return redirect(
            "Afrons:formulaire_verification_talent"
        )

    # Configuration Stripe.

    stripe.api_key = settings.STRIPE_SECRET_KEY

    prix_id = settings.STRIPE_PRIX_VERIFICATION_TALENT

    url_retour = request.build_absolute_uri(
        reverse("Afrons:formulaire_verification_talent")
    )

    try:

        session = stripe.checkout.Session.create(
            mode="payment",

            line_items=[
                {
                    "price": prix_id,
                    "quantity": 1,
                }
            ],

            success_url=(
                url_retour
                + "?paiement=retour"
                + "&session_id={CHECKOUT_SESSION_ID}"
            ),

            cancel_url=(
                url_retour
                + "?paiement=annule"
            ),

            client_reference_id=str(demande.identifiant),

            metadata={
                "type": "verification_talent",
                "demande_id": str(demande.identifiant),
                "talent_id": str(profil.pk),
            },
        )

        return redirect(session.url)

    except stripe.StripeError:

        logger.exception(
            "Erreur Stripe vérification Talent. "
            "Dossier ID=%s",
            demande.pk
        )

        messages.error(
            request,
            "Impossible de démarrer le paiement. "
            "Veuillez réessayer."
        )

        return redirect(
            "Afrons:formulaire_verification_talent"
        )






from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Commentaire,
    JaimeCommentaire,
    SignalementCommentaire,
)


# ============================================================
# AFROFANS — OUTILS COMMENTAIRES
# ============================================================

def video_commentaires_accessible(video_id):

    return get_object_or_404(
        videos_publiques(),
        pk=video_id,
    )


def commentaire_accessible(commentaire_id):

    commentaire = get_object_or_404(
        Commentaire.objects.select_related(
            "video",
            "utilisateur",
            "utilisateur__profil",
        ),
        pk=commentaire_id,
        est_visible=True,
    )

    video_commentaires_accessible(commentaire.video_id)

    return commentaire


from django.urls import reverse


# ============================================================
# AFROFANS — SÉRIALISATION DES COMMENTAIRES
# PHOTO ET NOM CLIQUABLES VERS LE PROFIL PUBLIC
# ============================================================

def serialiser_commentaire(commentaire, utilisateur):

    # --------------------------------------------------------
    # 1. RÉCUPÉRER L'AUTEUR DU COMMENTAIRE
    # --------------------------------------------------------

    auteur = commentaire.utilisateur

    profil = getattr(auteur, "profil", None)

    # --------------------------------------------------------
    # 2. PHOTO DE PROFIL
    # --------------------------------------------------------

    avatar = ""

    if profil and profil.avatar:

        try:
            avatar = profil.avatar.url

        except ValueError:
            avatar = ""

    # --------------------------------------------------------
    # 3. IDENTIFIANT EXACT DE L'UTILISATEUR
    # --------------------------------------------------------

    username = auteur.username

    # --------------------------------------------------------
    # 4. URL OFFICIELLE DU PROFIL AFROFANS
    # --------------------------------------------------------

    profil_url = reverse(
        "Afrons:profil_public",
        kwargs={
            "username": username
        }
    )

    # --------------------------------------------------------
    # 5. VÉRIFIER SI L'UTILISATEUR EST CONNECTÉ
    # --------------------------------------------------------

    est_connecte = utilisateur.is_authenticated

    # --------------------------------------------------------
    # 6. VÉRIFIER SI LE COMMENTAIRE LUI APPARTIENT
    # --------------------------------------------------------

    est_proprietaire = (
        est_connecte
        and commentaire.utilisateur_id == utilisateur.pk
    )

    # --------------------------------------------------------
    # 7. NOMBRE DE J'AIME DU COMMENTAIRE
    # --------------------------------------------------------

    nombre_jaimes = (
        commentaire.jaimes_commentaires.count()
    )

    # --------------------------------------------------------
    # 8. VÉRIFIER SI L'UTILISATEUR A AIMÉ
    # --------------------------------------------------------

    est_aime = False

    if est_connecte:

        est_aime = (
            commentaire.jaimes_commentaires.filter(
                utilisateur=utilisateur
            ).exists()
        )

    # --------------------------------------------------------
    # 9. RETOURNER LES INFORMATIONS AU JAVASCRIPT
    # --------------------------------------------------------

    return {

        # COMMENTAIRE

        "id": commentaire.pk,

        "parent_id": commentaire.reponse_a_id,

        # IDENTITÉ DE L'AUTEUR

        "auteur": username,

        "username": username,

        # PHOTO

        "avatar": avatar,

        # LIEN VERS SON VÉRITABLE PROFIL

        "profil_url": profil_url,

        # CONTENU

        "contenu": commentaire.contenu,

        # DATE

        "date": commentaire.cree_le.strftime(
            "%d/%m/%Y %H:%M"
        ),

        # PROPRIÉTAIRE DU COMMENTAIRE

        "est_proprietaire": est_proprietaire,

        # J'AIME

        "nombre_jaimes": nombre_jaimes,

        "est_aime": est_aime,
    }


# ============================================================
# LISTER LES COMMENTAIRES D'UNE VIDÉO
# ============================================================

@require_GET
def commentaires_video_ajax(request, video_id):

    video = video_commentaires_accessible(video_id)

    commentaires = (
        Commentaire.objects
        .filter(
            video=video,
            est_visible=True,
        )
        .select_related(
            "utilisateur",
            "utilisateur__profil",
        )
        .order_by("cree_le", "pk")[:300]
    )

    donnees = [
        serialiser_commentaire(c, request.user)
        for c in commentaires
    ]

    return JsonResponse({
        "success": True,
        "commentaires": donnees,
        "total": Commentaire.objects.filter(
            video=video,
            est_visible=True,
        ).count(),
    })


# ============================================================
# PUBLIER OU RÉPONDRE À UN COMMENTAIRE
# ============================================================

@login_required
@require_POST
def publier_commentaire_ajax(request, video_id):

    video = video_commentaires_accessible(video_id)

    contenu = request.POST.get("contenu", "").strip()

    if not contenu or len(contenu) > 500:
        return JsonResponse({
            "success": False,
            "erreur": "Le commentaire doit contenir entre "
                      "1 et 500 caractères.",
        }, status=400)

    parent_id = request.POST.get("parent_id", "").strip()

    parent = None

    if parent_id:

        parent = get_object_or_404(
            Commentaire,
            pk=parent_id,
            video=video,
            est_visible=True,
        )

    commentaire = Commentaire.objects.create(
        utilisateur=request.user,
        video=video,
        contenu=contenu,
        reponse_a=parent,
    )

    return JsonResponse({
        "success": True,
        "commentaire": serialiser_commentaire(
            commentaire,
            request.user,
        ),
        "total": Commentaire.objects.filter(
            video=video,
            est_visible=True,
        ).count(),
    }, status=201)


# ============================================================
# AIMER OU RETIRER UN J'AIME D'UN COMMENTAIRE
# ============================================================

@login_required
@require_POST
def aimer_commentaire_ajax(request, commentaire_id):

    commentaire = commentaire_accessible(commentaire_id)

    with transaction.atomic():

        aime, cree = JaimeCommentaire.objects.get_or_create(
            utilisateur=request.user,
            commentaire=commentaire,
        )

        if not cree:
            aime.delete()

        total = JaimeCommentaire.objects.filter(
            commentaire=commentaire,
        ).count()

    return JsonResponse({
        "success": True,
        "actif": cree,
        "total": total,
    })


# ============================================================
# SUPPRIMER SON PROPRE COMMENTAIRE
# ============================================================

@login_required
@require_POST
def supprimer_commentaire_ajax(request, commentaire_id):

    commentaire = commentaire_accessible(commentaire_id)

    if (
        commentaire.utilisateur_id != request.user.pk
        and not request.user.is_staff
    ):
        return JsonResponse({
            "success": False,
            "erreur": "Vous ne pouvez supprimer "
                      "que vos propres commentaires.",
        }, status=403)

    video = commentaire.video

    commentaire.delete()

    return JsonResponse({
        "success": True,
        "total": Commentaire.objects.filter(
            video=video,
            est_visible=True,
        ).count(),
    })


# ============================================================
# SIGNALER UN COMMENTAIRE
# ============================================================

import logging

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


# ============================================================
# AFROFANS — SIGNALER UN COMMENTAIRE
# ============================================================

@login_required
@require_POST
def signaler_commentaire_ajax(request, commentaire_id):

    # 1. RÉCUPÉRER LE COMMENTAIRE
    try:
        commentaire = commentaire_accessible(commentaire_id)

    except Exception:
        return JsonResponse({
            "success": False,
            "erreur": "Ce commentaire est introuvable "
                      "ou n'est plus accessible.",
        }, status=404)

    # 2. INTERDIRE DE SIGNALER SON PROPRE COMMENTAIRE
    if commentaire.utilisateur_id == request.user.pk:

        return JsonResponse({
            "success": False,
            "erreur": "Vous ne pouvez pas signaler "
                      "votre propre commentaire.",
        }, status=400)

    # 3. RÉCUPÉRER ET VALIDER LE MOTIF
    motif = request.POST.get("motif", "").strip()

    motifs_autorises = dict(
        SignalementCommentaire.MOTIFS
    )

    if motif not in motifs_autorises:

        return JsonResponse({
            "success": False,
            "erreur": "Veuillez sélectionner un motif "
                      "de signalement valide.",
        }, status=400)

    # 4. RÉCUPÉRER LES DÉTAILS
    details = request.POST.get(
        "details", ""
    ).strip()

    if len(details) > 500:

        return JsonResponse({
            "success": False,
            "erreur": "Les détails ne doivent pas "
                      "dépasser 500 caractères.",
        }, status=400)

    # 5. ENREGISTRER LE SIGNALEMENT
    try:

        with transaction.atomic():

            signalement, cree = (
                SignalementCommentaire.objects
                .get_or_create(
                    auteur=request.user,
                    commentaire=commentaire,
                    defaults={
                        "motif": motif,
                        "details": details,
                    },
                )
            )

            if not cree:

                return JsonResponse({
                    "success": False,
                    "erreur": "Vous avez déjà signalé "
                              "ce commentaire.",
                }, status=409)

    except IntegrityError:

        return JsonResponse({
            "success": False,
            "erreur": "Ce commentaire a déjà été signalé "
                      "par votre compte.",
        }, status=409)

    except Exception:

        logger.exception(
            "Erreur lors du signalement d'un commentaire "
            "AfroFans. Utilisateur=%s, commentaire=%s",
            request.user.pk,
            commentaire_id,
        )

        return JsonResponse({
            "success": False,
            "erreur": "Une erreur technique est survenue. "
                      "Veuillez réessayer.",
        }, status=500)

    # 6. CONFIRMATION
    return JsonResponse({
        "success": True,
        "message": "Merci. Votre signalement a été transmis "
                   "à l'équipe de modération AfroFans "
                   "pour examen.",
    }, status=201)




from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import (
    PresenceAfroFans,
    PresenceSpectateur,
    PresenceMessage,
    PresenceJaime,
)


STICKERS_PRESENCE = {
    "coeur": "❤️",
    "flamme": "🔥",
    "couronne": "👑",
    "applaudissement": "👏",
    "etoile": "⭐",
    "rose": "🌹",
}


def nombre_spectateurs_presence(presence):
    limite = timezone.now() - timedelta(seconds=45)

    return PresenceSpectateur.objects.filter(
        presence=presence,
        derniere_activite__gte=limite
    ).count()


def serialiser_message_presence(message):

    profil = getattr(message.auteur, "profil", None)
    avatar = ""

    if profil and profil.avatar:
        try:
            avatar = profil.avatar.url
        except ValueError:
            pass

    return {
        "id": message.pk,
        "auteur": message.auteur.username,
        "avatar": avatar,
        "type": message.type_message,
        "contenu": message.contenu,
        "sticker": STICKERS_PRESENCE.get(message.sticker, ""),
        "date": message.cree_le.strftime("%H:%M"),
    }


@require_GET
def presences(request):

    presences_actives = (
        PresenceAfroFans.objects
        .filter(est_active=True)
        .select_related("talent")
        .order_by("-cree_le")
    )

    return render(
        request,
        "Afrons/presences.html",
        {
            "presences": presences_actives,
        }
    )


@require_GET
def presence_detail(request, presence_id):

    presence = get_object_or_404(
        PresenceAfroFans.objects.select_related("talent"),
        pk=presence_id
    )

    return render(
        request,
        "Afrons/presence_direct.html",
        {
            "presence": presence,
            "nombre_spectateurs": nombre_spectateurs_presence(
                presence
            ),
            "nombre_jaimes": presence.jaimes_presence.count(),
        }
    )


@login_required
@require_POST
def demarrer_presence(request):

    profil = getattr(request.user, "profil", None)

    if not profil or profil.type_compte != "createur":
        return JsonResponse({
            "success": False,
            "erreur": "Seuls les comptes Talent peuvent "
                      "créer une présence."
        }, status=403)

    sujet = request.POST.get("sujet", "").strip()
    description = request.POST.get("description", "").strip()
    url_video = request.POST.get("url_video", "").strip()

    if not sujet or len(sujet) > 160:
        return JsonResponse({
            "success": False,
            "erreur": "Veuillez indiquer un sujet valide."
        }, status=400)

    if len(description) > 2000:
        return JsonResponse({
            "success": False,
            "erreur": "Description trop longue."
        }, status=400)

    # L'URL doit pointer vers une source vidéo autorisée.
    # En production, la diffusion réelle doit être gérée
    # par un service vidéo avec authentification.

    if url_video and not url_video.startswith("https://"):
        return JsonResponse({
            "success": False,
            "erreur": "La source vidéo doit utiliser HTTPS."
        }, status=400)

    with transaction.atomic():

        PresenceAfroFans.objects.select_for_update().filter(
            talent=request.user,
            est_active=True
        ).update(
            est_active=False,
            terminee_le=timezone.now()
        )

        presence = PresenceAfroFans.objects.create(
            talent=request.user,
            sujet=sujet,
            description=description,
            url_video=url_video
        )

    # Connecter ici les notifications des abonnés,
    # en utilisant le modèle d'abonnement AfroFans existant.

    return JsonResponse({
        "success": True,
        "presence_id": presence.pk,
        "url": f"/presence/{presence.pk}/",
    }, status=201)


@require_POST
def presence_heartbeat(request, presence_id):

    presence = get_object_or_404(
        PresenceAfroFans,
        pk=presence_id
    )

    if not presence.est_active:
        return JsonResponse({
            "success": True,
            "est_active": False,
            "spectateurs": 0
        })

    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key

    PresenceSpectateur.objects.update_or_create(
        presence=presence,
        session_id=session_id,
        defaults={
            "derniere_activite": timezone.now()
        }
    )

    return JsonResponse({
        "success": True,
        "est_active": True,
        "spectateurs": nombre_spectateurs_presence(presence)
    })


@require_GET
def presence_etat(request, presence_id):

    presence = get_object_or_404(
        PresenceAfroFans,
        pk=presence_id
    )

    try:
        apres_id = max(
            0,
            int(request.GET.get("apres", 0))
        )
    except (ValueError, TypeError):
        apres_id = 0

    messages = list(
        PresenceMessage.objects
        .filter(
            presence=presence,
            pk__gt=apres_id
        )
        .select_related("auteur")
        .order_by("pk")[:100]
    )

    return JsonResponse({
        "success": True,
        "est_active": presence.est_active,
        "spectateurs": nombre_spectateurs_presence(presence),
        "jaimes": presence.jaimes_presence.count(),
        "messages": [
            serialiser_message_presence(message)
            for message in messages
        ],
    })


from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

# Conserver les imports existants :
# PresenceAfroFans, PresenceJaime, PresenceMessage
# et serialiser_message_presence


# ============================================================
# AFROFANS — STICKERS AUTORISÉS
# ============================================================

STICKERS_PRESENCE = {
    "lion": "🦁",
    "sapin": "🌲",
    "roi": "👑",
    "montre": "⌚",
    "lunettes": "🕶️",
    "chaine": "📿",
    "livre": "📖",
}


# ============================================================
# AFROFANS — INTERACTIONS EN PRÉSENCE
#
# ACTIONS :
# 1. JAIME
# 2. COMMENTAIRE
# 3. STICKER
# ============================================================

@login_required
@require_POST
def presence_interaction(request, presence_id):

    # --------------------------------------------------------
    # 1. RÉCUPÉRER LA PRÉSENCE
    # --------------------------------------------------------

    presence = get_object_or_404(
        PresenceAfroFans,
        pk=presence_id
    )

    # --------------------------------------------------------
    # 2. VÉRIFIER SI LA PRÉSENCE EST ACTIVE
    # --------------------------------------------------------

    if not presence.est_active:

        return JsonResponse({
            "success": False,
            "erreur": "Cette présence est terminée."
        }, status=409)

    # --------------------------------------------------------
    # 3. IDENTIFIER L'ACTION
    # --------------------------------------------------------

    action = request.POST.get(
        "action", ""
    ).strip().lower()

    # ========================================================
    # 4. J'AIME
    # ========================================================

    if action == "jaime":

        with transaction.atomic():

            jaime, cree = PresenceJaime.objects.get_or_create(
                presence=presence,
                utilisateur=request.user
            )

            if not cree:
                jaime.delete()

            total = PresenceJaime.objects.filter(
                presence=presence
            ).count()

        return JsonResponse({
            "success": True,
            "actif": cree,
            "total": total,
            "message": (
                "Vous aimez cette présence."
                if cree
                else "Votre J'aime a été retiré."
            )
        })

    # ========================================================
    # 5. COMMENTAIRES
    # ========================================================

    if action == "commentaire":

        contenu = request.POST.get(
            "contenu", ""
        ).strip()

        if not contenu or len(contenu) > 500:

            return JsonResponse({
                "success": False,
                "erreur": (
                    "Commentaire invalide. "
                    "500 caractères maximum."
                )
            }, status=400)

        message = PresenceMessage.objects.create(
            presence=presence,
            auteur=request.user,
            type_message="commentaire",
            contenu=contenu
        )

        return JsonResponse({
            "success": True,
            "message": serialiser_message_presence(
                message
            )
        }, status=201)

    # ========================================================
    # 6. STICKERS AFROFANS
    # ========================================================

    if action == "sticker":

        code_sticker = request.POST.get(
            "sticker", ""
        ).strip().lower()

        # Vérifier que le sticker existe
        if code_sticker not in STICKERS_PRESENCE:

            return JsonResponse({
                "success": False,
                "erreur": "Ce sticker n'est pas autorisé."
            }, status=400)

        # Récupérer l'emoji correspondant
        emoji = STICKERS_PRESENCE[code_sticker]

        # Enregistrer le sticker dans la présence
        message = PresenceMessage.objects.create(
            presence=presence,
            auteur=request.user,
            type_message="sticker",
            sticker=code_sticker
        )

        # Sérialiser le message enregistré
        message_data = serialiser_message_presence(
            message
        )

        # Fournir également l'emoji au navigateur
        message_data["sticker"] = emoji
        message_data["type"] = "sticker"

        return JsonResponse({
            "success": True,
            "sticker": code_sticker,
            "emoji": emoji,
            "message": message_data
        }, status=201)

    # ========================================================
    # 7. ACTION INCONNUE
    # ========================================================

    return JsonResponse({
        "success": False,
        "erreur": "Action non reconnue."
    }, status=400)


@login_required
@require_POST
def terminer_presence(request, presence_id):

    presence = get_object_or_404(
        PresenceAfroFans,
        pk=presence_id,
        talent=request.user
    )

    if presence.est_active:
        presence.terminer()

    return JsonResponse({
        "success": True,
        "message": "Présence terminée."
    })





# ============================================================
# AFROFANS — LIVEKIT
# CAMÉRA / MICRO DU TALENT
# VIDÉO ET AUDIO POUR LES FANS
# ============================================================

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from livekit import api

from .models import PresenceAfroFans


@login_required
@require_POST
def presence_livekit_token(request, presence_id):

    # --------------------------------------------------------
    # 1. RÉCUPÉRER LA PRÉSENCE
    # --------------------------------------------------------

    presence = get_object_or_404(
        PresenceAfroFans,
        pk=presence_id
    )

    # --------------------------------------------------------
    # 2. VÉRIFIER SI LA PRÉSENCE EST ACTIVE
    # --------------------------------------------------------

    if not presence.est_active:

        return JsonResponse(
            {
                "success": False,
                "erreur": "Cette présence est terminée."
            },
            status=409
        )

    # --------------------------------------------------------
    # 3. CONFIGURATION LIVEKIT
    # --------------------------------------------------------

    livekit_url = getattr(
        settings,
        "LIVEKIT_URL",
        ""
    )

    api_key = getattr(
        settings,
        "LIVEKIT_API_KEY",
        ""
    )

    api_secret = getattr(
        settings,
        "LIVEKIT_API_SECRET",
        ""
    )

    if not all([
        livekit_url,
        api_key,
        api_secret
    ]):

        return JsonResponse(
            {
                "success": False,
                "erreur": (
                    "Le serveur de diffusion AfroFans "
                    "n'est pas encore configuré."
                )
            },
            status=503
        )

    # --------------------------------------------------------
    # 4. IDENTIFIER LE TALENT
    # --------------------------------------------------------

    est_talent = (
        request.user.pk == presence.talent_id
    )

    # --------------------------------------------------------
    # 5. IDENTIFIANT UNIQUE DE LA SALLE
    # --------------------------------------------------------

    room_name = f"afrofans-presence-{presence.pk}"

    # --------------------------------------------------------
    # 6. PERMISSIONS
    #
    # TALENT :
    # - publier caméra
    # - publier microphone
    #
    # FAN :
    # - regarder
    # - écouter
    # - aucune publication média
    # --------------------------------------------------------

    permissions = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=est_talent,
        can_subscribe=True,
        can_publish_data=False,
        can_publish_sources=(
            ["camera", "microphone"]
            if est_talent
            else None
        )
    )

    # --------------------------------------------------------
    # 7. GÉNÉRER UN JETON TEMPORAIRE
    # --------------------------------------------------------

    try:

        token = (
            api.AccessToken(
                api_key,
                api_secret
            )
            .with_identity(
                f"user-{request.user.pk}"
            )
            .with_name(
                request.user.username
            )
            .with_grants(permissions)
            .with_ttl(
                timedelta(minutes=30)
            )
            .to_jwt()
        )

    except Exception:

        return JsonResponse(
            {
                "success": False,
                "erreur": (
                    "Impossible de créer l'accès "
                    "à la présence."
                )
            },
            status=500
        )

    # --------------------------------------------------------
    # 8. RÉPONSE AU NAVIGATEUR
    # --------------------------------------------------------

    return JsonResponse({
        "success": True,
        "livekit_url": livekit_url,
        "token": token,
        "room_name": room_name,
        "est_talent": est_talent,
    })






import logging

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import AchatTelechargementVideo, Video
from .forms import AchatTelechargementVideoForm

logger = logging.getLogger(__name__)


@login_required
def acheter_telechargement_video(request, video_id):

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
        statut_traitement__in=("termine", "non_requis"),
    )

    # Le propriétaire ne doit pas acheter sa vidéo.
    if video.auteur_id == request.user.pk:
        messages.info(
            request,
            "Cette vidéo vous appartient."
        )
        return redirect(
            "Afrons:detail_video",
            video.pk
        )

    # Déjà payé : accès à la confirmation.
    achat_paye = AchatTelechargementVideo.objects.filter(
        acheteur=request.user,
        video=video,
        statut="paye",
    ).first()

    if achat_paye:
        return redirect(
            "Afrons:confirmation_telechargement_video",
            achat_paye.pk,
        )

    formulaire = AchatTelechargementVideoForm(
        request.POST or None
    )

    if request.method != "POST":
        return render(
            request,
            "Afrons/acheter_telechargement_video.html",
            {
                "video": video,
                "formulaire": formulaire,
            },
        )

    # Utiliser CAD ou EUR.
    # Ne pas accepter XOF dans cette intégration.
    devise = request.POST.get(
        "devise", "CAD"
    ).strip().upper()

    if devise not in ("CAD", "EUR"):
        messages.error(
            request,
            "Choisissez CAD ou EUR pour payer par carte."
        )
        return redirect(
            "Afrons:acheter_telechargement_video",
            video.pk,
        )

    if not getattr(
        settings,
        "AFROFANS_PAIEMENTS_VIDEOS_ACTIFS",
        False,
    ):
        messages.error(
            request,
            "Le paiement des vidéos n'est pas encore activé."
        )
        return redirect(
            "Afrons:detail_video",
            video.pk,
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        with transaction.atomic():

            achat, cree = (
                AchatTelechargementVideo.objects.get_or_create(
                    acheteur=request.user,
                    video=video,
                    devise=devise,
                    defaults={
                        "methode_paiement": "carte",
                        "statut": "en_attente",
                    },
                )
            )

            # Bloquer les achats dans un état incompatible.
            if achat.statut != "en_attente":
                messages.error(
                    request,
                    "Cette transaction ne peut pas être relancée."
                )
                return redirect(
                    "Afrons:confirmation_telechargement_video",
                    achat.pk,
                )

            # Réutiliser une session de paiement ouverte.
            if achat.reference_paiement.startswith("cs_"):

                session_existante = (
                    stripe.checkout.Session.retrieve(
                        achat.reference_paiement
                    )
                )

                if session_existante.status == "open":
                    return redirect(
                        session_existante.url
                    )

                if session_existante.status == "complete":
                    messages.info(
                        request,
                        "Nous attendons la confirmation Stripe."
                    )
                    return redirect(
                        "Afrons:confirmation_telechargement_video",
                        achat.pk,
                    )

                # Une session expirée peut être remplacée.
                achat.reference_paiement = ""
                achat.save(
                    update_fields=["reference_paiement"]
                )

            # Le modèle calcule déjà le montant total.
            montant_centimes = int(
                achat.montant_total * 100
            )

            if montant_centimes <= 0:
                raise ValueError(
                    "Montant de paiement invalide."
                )

            url_confirmation = request.build_absolute_uri(
                reverse(
                    "Afrons:confirmation_telechargement_video",
                    args=[achat.pk],
                )
            )

            url_annulation = request.build_absolute_uri(
                reverse(
                    "Afrons:acheter_telechargement_video",
                    args=[video.pk],
                )
            )

            # Création réelle de Stripe Checkout.
            session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": devise.lower(),
                        "unit_amount": montant_centimes,
                        "product_data": {
                            "name": (
                                f"Téléchargement AfroFans — "
                                f"{video.titre[:100]}"
                            ),
                        },
                    },
                    "quantity": 1,
                }],
                customer_email=(
                    request.user.email or None
                ),
                client_reference_id=str(achat.pk),
                metadata={
                    "type": "telechargement_video",
                    "achat_id": str(achat.pk),
                    "video_id": str(video.pk),
                },
                success_url=url_confirmation,
                cancel_url=url_annulation,
            )

            achat.reference_paiement = session.id
            achat.methode_paiement = "carte"
            achat.save(update_fields=[
                "reference_paiement",
                "methode_paiement",
            ])

        # Le fan arrive sur la page de paiement Stripe.
        return redirect(session.url)

    except (stripe.StripeError, ValueError):
        logger.exception(
            "Erreur Stripe achat vidéo %s",
            video.pk,
        )
        messages.error(
            request,
            "Impossible de démarrer le paiement Stripe."
        )

        return redirect(
            "Afrons:detail_video",
            video.pk,
        )





from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

import stripe
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook_telechargement_video(request):

    secret = getattr(
        settings,
        "STRIPE_WEBHOOK_SECRET_VIDEOS",
        "",
    )

    if not secret:
        return HttpResponse(
            "Webhook non configuré.",
            status=503,
        )

    try:
        evenement = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            secret,
        )

    except (
        ValueError,
        stripe.SignatureVerificationError,
    ):
        return HttpResponse(status=400)

    if evenement["type"] not in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        return HttpResponse(status=200)

    session = evenement["data"]["object"]

    if session.get("payment_status") != "paid":
        return HttpResponse(status=200)

    metadata = session.get("metadata") or {}

    if metadata.get("type") != "telechargement_video":
        return HttpResponse(status=200)

    try:
        achat_id = int(metadata["achat_id"])

        with transaction.atomic():

            achat = (
                AchatTelechargementVideo.objects
                .select_for_update()
                .get(pk=achat_id)
            )

            # Éviter de confirmer une autre transaction.
            if achat.reference_paiement != session["id"]:
                return HttpResponse(status=400)

            if metadata.get("video_id") != str(achat.video_id):
                return HttpResponse(status=400)

            montant_attendu = int(
                achat.montant_total * 100
            )

            if (
                session.get("amount_total") != montant_attendu
                or session.get("currency") != achat.devise.lower()
            ):
                logger.error(
                    "Montant ou devise invalide : achat %s",
                    achat.pk,
                )
                return HttpResponse(status=400)

            # Idempotence : ne pas créditer deux fois.
            if achat.statut == "paye":
                return HttpResponse(status=200)

            if achat.statut != "en_attente":
                return HttpResponse(status=409)

            achat.statut = "paye"
            achat.paye_le = timezone.now()

            achat.save(update_fields=[
                "statut",
                "paye_le",
            ])

            logger.info(
                "Téléchargement AfroFans payé : %s",
                achat.pk,
            )

    except AchatTelechargementVideo.DoesNotExist:
        return HttpResponse(status=404)

    except Exception:
        logger.exception(
            "Erreur webhook achat vidéo AfroFans"
        )
        return HttpResponse(status=500)

    return HttpResponse(status=200)
