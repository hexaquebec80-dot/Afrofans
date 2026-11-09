
# ============================================================
# AFROFANS MOBILE — API REST V1
# Connexion / profil / événements publics
# ============================================================

from django.contrib.auth import authenticate

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.authtoken.models import Token

from .models import Evenement



# ============================================================
# AFROFANS MOBILE — API DU FLUX VIDÉO
# Vidéos réelles, talents, commentaires et interactions
# ============================================================

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from .models import (
    Video,
    Jaime,
    Favori,
    Abonnement,
    Commentaire,
    JaimeCommentaire,
    SignalementCommentaire,
)


# ============================================================
# 1. CONVERTIR UNE IMAGE OU VIDÉO EN URL
# ============================================================

def mobile_media_url(request, fichier):

    if not fichier:
        return None

    try:
        url = fichier.url

        if callable(url):
            url = url()

        if not url:
            return None

        return request.build_absolute_uri(str(url))

    except (ValueError, AttributeError, TypeError):
        return None


# ============================================================
# 2. VIDÉOS PUBLIÉES — FLUX MOBILE
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def videos_mobile(request):

    # --------------------------------------------------------
    # A. VIDÉOS RÉELLEMENT PUBLIÉES
    # --------------------------------------------------------

    videos = (
        Video.objects
        .filter(est_publiee=True)
        .select_related(
            "auteur",
            "auteur__profil",
            "musique",
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

    # --------------------------------------------------------
    # B. ONGLETS DU FLUX
    # --------------------------------------------------------

    onglet = request.query_params.get(
        "onglet",
        "pour-toi",
    )

    if onglet not in (
        "pour-toi",
        "suivis",
        "tendances",
    ):
        onglet = "pour-toi"

    if onglet == "suivis":

        if request.user.is_authenticated:

            createurs_suivis = (
                Abonnement.objects
                .filter(fan=request.user)
                .values_list(
                    "createur_id",
                    flat=True,
                )
            )

            videos = videos.filter(
                auteur_id__in=createurs_suivis
            )

        else:
            videos = videos.none()

    # --------------------------------------------------------
    # C. RECHERCHE ET CATÉGORIE
    # --------------------------------------------------------

    recherche = request.query_params.get(
        "q",
        "",
    ).strip()[:100]

    categorie = request.query_params.get(
        "categorie",
        "",
    ).strip()

    if recherche:

        videos = videos.filter(
            Q(titre__icontains=recherche)
            | Q(description__icontains=recherche)
            | Q(hashtags__icontains=recherche)
            | Q(
                auteur__username__icontains=recherche
            )
        )

    if categorie:

        videos = videos.filter(
            categorie=categorie
        )

    # --------------------------------------------------------
    # D. ÉTAT DES INTERACTIONS DE L'UTILISATEUR
    # --------------------------------------------------------

    if request.user.is_authenticated:

        videos = videos.annotate(
            mobile_est_aime=Exists(
                Jaime.objects.filter(
                    utilisateur=request.user,
                    video_id=OuterRef("pk"),
                )
            ),
            mobile_est_favori=Exists(
                Favori.objects.filter(
                    utilisateur=request.user,
                    video_id=OuterRef("pk"),
                )
            ),
            mobile_est_abonne=Exists(
                Abonnement.objects.filter(
                    fan=request.user,
                    createur_id=OuterRef("auteur_id"),
                )
            ),
        )

    # --------------------------------------------------------
    # E. CLASSEMENT
    # --------------------------------------------------------

    if onglet == "tendances":

        videos = videos.order_by(
            "-vues",
            "-creee_le",
            "-pk",
        )

    else:

        videos = videos.order_by(
            "-creee_le",
            "-pk",
        )

    # --------------------------------------------------------
    # F. PAGINATION
    # --------------------------------------------------------

    try:
        page = max(
            1,
            min(
                int(
                    request.query_params.get(
                        "page",
                        1,
                    )
                ),
                10000,
            ),
        )
    except (ValueError, TypeError):
        page = 1

    limite = 30

    debut = (page - 1) * limite
    fin = debut + limite + 1

    videos_page = list(
        videos[debut:fin]
    )

    page_suivante = len(videos_page) > limite

    videos_page = videos_page[:limite]

    # --------------------------------------------------------
    # G. SÉRIALISATION DES VRAIES VIDÉOS
    # --------------------------------------------------------

    resultat = []

    for video in videos_page:

        fichier = getattr(
            video,
            "fichier_diffuse",
            None,
        )

        video_url = mobile_media_url(
            request,
            fichier,
        )

        if not video_url:
            continue

        auteur = video.auteur

        profil = getattr(
            auteur,
            "profil",
            None,
        )

        avatar = getattr(
            profil,
            "avatar",
            None,
        )

        miniature = getattr(
            video,
            "miniature",
            None,
        )

        musique = getattr(
            video,
            "musique",
            None,
        )

        username = auteur.get_username()

        profil_url = request.build_absolute_uri(
            reverse(
                "Afrons:profil_public",
                kwargs={
                    "username": username,
                },
            )
        )

        resultat.append({

            # ------------------------------
            # IDENTITÉ VIDÉO
            # ------------------------------

            "id": video.pk,

            "video_url": video_url,

            "miniature_url": mobile_media_url(
                request,
                miniature,
            ),

            "titre": video.titre,

            "description": (
                video.description or ""
            ),

            "hashtags": str(
                getattr(
                    video,
                    "hashtags",
                    "",
                ) or ""
            ),

            "categorie": getattr(
                video,
                "categorie",
                "",
            ),

            # ------------------------------
            # AUTEUR / TALENT
            # ------------------------------

            "auteur": username,

            "auteur_id": auteur.pk,

            "nom_public": (
                getattr(
                    profil,
                    "nom_public",
                    None,
                )
                or username
            ),

            "profil_url": profil_url,

            "avatar_url": mobile_media_url(
                request,
                avatar,
            ),

            "est_certifie": bool(
                getattr(
                    profil,
                    "est_certifie",
                    False,
                )
            ),

            # ------------------------------
            # STATISTIQUES RÉELLES
            # ------------------------------

            "nombre_jaimes": (
                video.nombre_jaimes
            ),

            "nombre_commentaires": (
                video.nombre_commentaires
            ),

            "nombre_partages": (
                getattr(
                    video,
                    "nombre_partages",
                    0,
                ) or 0
            ),

            "vues": (
                video.vues or 0
            ),

            # ------------------------------
            # INTERACTIONS UTILISATEUR
            # ------------------------------

            "est_aime": bool(
                getattr(
                    video,
                    "mobile_est_aime",
                    False,
                )
            ),

            "est_favori": bool(
                getattr(
                    video,
                    "mobile_est_favori",
                    False,
                )
            ),

            "est_abonne": bool(
                getattr(
                    video,
                    "mobile_est_abonne",
                    False,
                )
            ),

            "autoriser_commentaires": (
                video.autoriser_commentaires
            ),

            # ------------------------------
            # MUSIQUE
            # ------------------------------

            "musique": (
                musique.titre
                if musique
                else "Son original"
            ),

            # ------------------------------
            # PUBLICATION
            # ------------------------------

            "creee_le": (
                video.creee_le.isoformat()
            ),

        })

    # --------------------------------------------------------
    # H. RÉPONSE JSON
    # --------------------------------------------------------

    return Response({

        "success": True,

        "onglet": onglet,

        "page": page,

        "has_next": page_suivante,

        "videos": resultat,

    })


# ============================================================
# 3. AIMER / RETIRER UN J'AIME
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aimer_video_mobile(request, video_id):

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
    )

    with transaction.atomic():

        jaime, cree = (
            Jaime.objects.get_or_create(
                utilisateur=request.user,
                video=video,
            )
        )

        if not cree:
            jaime.delete()

        total = Jaime.objects.filter(
            video=video
        ).count()

    return Response({
        "success": True,
        "actif": cree,
        "est_aime": cree,
        "total": total,
        "nombre_jaimes": total,
    })


# ============================================================
# 4. AJOUTER / RETIRER UN FAVORI
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def favori_video_mobile(request, video_id):

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
    )

    with transaction.atomic():

        favori, cree = (
            Favori.objects.get_or_create(
                utilisateur=request.user,
                video=video,
            )
        )

        if not cree:
            favori.delete()

    return Response({
        "success": True,
        "actif": cree,
        "est_favori": cree,
    })


# ============================================================
# 5. SUIVRE / NE PLUS SUIVRE UN TALENT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def suivre_talent_mobile(request, username):

    Utilisateur = get_user_model()

    createur = get_object_or_404(
        Utilisateur,
        username=username,
    )

    if createur.pk == request.user.pk:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Tu ne peux pas te suivre."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    profil = getattr(
        createur,
        "profil",
        None,
    )

    if getattr(
        profil,
        "type_compte",
        None,
    ) != "createur":

        return Response(
            {
                "success": False,
                "erreur": (
                    "Ce compte n'est pas un Talent."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():

        abonnement, cree = (
            Abonnement.objects.get_or_create(
                fan=request.user,
                createur=createur,
            )
        )

        if not cree:
            abonnement.delete()

        total = Abonnement.objects.filter(
            createur=createur
        ).count()

    return Response({
        "success": True,
        "actif": cree,
        "est_abonne": cree,
        "nombre_abonnes": total,
    })


# ============================================================
# 6. SÉRIALISER UN COMMENTAIRE
# ============================================================

def serialiser_commentaire_mobile(
    request,
    commentaire,
):

    utilisateur = commentaire.utilisateur

    profil = getattr(
        utilisateur,
        "profil",
        None,
    )

    username = utilisateur.get_username()

    profil_url = request.build_absolute_uri(
        reverse(
            "Afrons:profil_public",
            kwargs={
                "username": username,
            },
        )
    )

    nombre_jaimes = (
        commentaire.jaimes_commentaires.count()
    )

    est_aime = False

    if request.user.is_authenticated:

        est_aime = (
            commentaire.jaimes_commentaires
            .filter(
                utilisateur=request.user
            )
            .exists()
        )

    return {
        "id": commentaire.pk,

        "parent_id": (
            commentaire.reponse_a_id
        ),

        "auteur": username,

        "username": username,

        "nom_public": (
            getattr(
                profil,
                "nom_public",
                None,
            )
            or username
        ),

        "avatar": mobile_media_url(
            request,
            getattr(
                profil,
                "avatar",
                None,
            ),
        ),

        "profil_url": profil_url,

        "contenu": commentaire.contenu,

        "date": (
            commentaire.cree_le.isoformat()
        ),

        "est_proprietaire": (
            request.user.is_authenticated
            and commentaire.utilisateur_id
            == request.user.pk
        ),

        "nombre_jaimes": nombre_jaimes,

        "est_aime": est_aime,
    }


# ============================================================
# 7. AFFICHER / PUBLIER / RÉPONDRE AUX COMMENTAIRES
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def commentaires_video_mobile(request, video_id):

    video = get_object_or_404(
        Video,
        pk=video_id,
        est_publiee=True,
    )

    # --------------------------------------------------------
    # GET : LISTER LES COMMENTAIRES
    # --------------------------------------------------------

    if request.method == "GET":

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
            .order_by(
                "cree_le",
                "pk",
            )[:300]
        )

        resultat = [
            serialiser_commentaire_mobile(
                request,
                commentaire,
            )
            for commentaire in commentaires
        ]

        return Response({
            "success": True,
            "commentaires": resultat,
            "total": (
                Commentaire.objects.filter(
                    video=video,
                    est_visible=True,
                ).count()
            ),
        })

    # --------------------------------------------------------
    # POST : AJOUTER UN COMMENTAIRE
    # --------------------------------------------------------

    if not video.autoriser_commentaires:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Les commentaires sont désactivés."
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    contenu = request.data.get(
        "contenu",
        "",
    )

    if not isinstance(contenu, str):
        contenu = ""

    contenu = contenu.strip()

    if not contenu or len(contenu) > 500:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Le commentaire doit contenir "
                    "entre 1 et 500 caractères."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    parent_id = request.data.get(
        "parent_id",
        None,
    )

    parent = None

    if parent_id not in (None, ""):

        try:
            parent_id = int(parent_id)
        except (ValueError, TypeError):

            return Response(
                {
                    "success": False,
                    "erreur": "Réponse invalide.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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

    return Response(
        {
            "success": True,
            "commentaire": (
                serialiser_commentaire_mobile(
                    request,
                    commentaire,
                )
            ),
            "total": (
                Commentaire.objects.filter(
                    video=video,
                    est_visible=True,
                ).count()
            ),
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# 8. AIMER / RETIRER UN J'AIME D'UN COMMENTAIRE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aimer_commentaire_mobile(request, commentaire_id):

    commentaire = get_object_or_404(
        Commentaire,
        pk=commentaire_id,
        est_visible=True,
        video__est_publiee=True,
    )

    with transaction.atomic():

        jaime, cree = (
            JaimeCommentaire.objects.get_or_create(
                utilisateur=request.user,
                commentaire=commentaire,
            )
        )

        if not cree:
            jaime.delete()

        total = JaimeCommentaire.objects.filter(
            commentaire=commentaire
        ).count()

    return Response({
        "success": True,
        "actif": cree,
        "est_aime": cree,
        "total": total,
    })


# ============================================================
# 9. SUPPRIMER SON COMMENTAIRE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def supprimer_commentaire_mobile(
    request,
    commentaire_id,
):

    commentaire = get_object_or_404(
        Commentaire,
        pk=commentaire_id,
        est_visible=True,
        video__est_publiee=True,
    )

    if (
        commentaire.utilisateur_id
        != request.user.pk
        and not request.user.is_staff
    ):

        return Response(
            {
                "success": False,
                "erreur": (
                    "Tu ne peux pas supprimer "
                    "ce commentaire."
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    video_id = commentaire.video_id

    commentaire.delete()

    total = Commentaire.objects.filter(
        video_id=video_id,
        est_visible=True,
    ).count()

    return Response({
        "success": True,
        "total": total,
    })


# ============================================================
# 10. SIGNALER UN COMMENTAIRE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def signaler_commentaire_mobile(
    request,
    commentaire_id,
):

    commentaire = get_object_or_404(
        Commentaire,
        pk=commentaire_id,
        est_visible=True,
        video__est_publiee=True,
    )

    if commentaire.utilisateur_id == request.user.pk:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Tu ne peux pas signaler "
                    "ton propre commentaire."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    motif = request.data.get("motif", "")
    details = request.data.get("details", "")

    if not isinstance(motif, str):
        motif = ""

    if not isinstance(details, str):
        details = ""

    motif = motif.strip()
    details = details.strip()

    motifs_autorises = dict(
        SignalementCommentaire.MOTIFS
    )

    if motif not in motifs_autorises:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Motif de signalement invalide."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(details) > 500:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Les détails ne doivent pas "
                    "dépasser 500 caractères."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

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

                return Response(
                    {
                        "success": False,
                        "erreur": (
                            "Commentaire déjà signalé."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

    except IntegrityError:

        return Response(
            {
                "success": False,
                "erreur": (
                    "Commentaire déjà signalé."
                ),
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "success": True,
            "message": (
                "Signalement transmis "
                "à la modération AfroFans."
            ),
        },
        status=status.HTTP_201_CREATED,
    )





class LoginMobileThrottle(AnonRateThrottle):
    rate = "5/minute"


# ============================================================
# 1. CONNEXION DES FANS ET TALENTS
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginMobileThrottle])
def connexion_mobile(request):

    username = request.data.get("username", "")
    password = request.data.get("password", "")

    if not isinstance(username, str):
        username = ""

    if not isinstance(password, str):
        password = ""

    utilisateur = authenticate(
        request,
        username=username.strip(),
        password=password,
    )

    if utilisateur is None or not utilisateur.is_active:

        return Response(
            {
                "detail": "Identifiants incorrects."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(
        user=utilisateur
    )

    profil = getattr(
        utilisateur,
        "profil",
        None,
    )

    return Response({
        "token": token.key,
        "username": utilisateur.get_username(),
        "type_compte": getattr(
            profil,
            "type_compte",
            "fan",
        ),
    })


# ============================================================
# 2. PROFIL DE L'UTILISATEUR
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profil_mobile(request):

    utilisateur = request.user

    profil = getattr(
        utilisateur,
        "profil",
        None,
    )

    return Response({
        "id": utilisateur.pk,
        "username": utilisateur.get_username(),
        "nom": utilisateur.get_full_name(),
        "type_compte": getattr(
            profil,
            "type_compte",
            "fan",
        ),
        "est_certifie": getattr(
            profil,
            "est_certifie",
            False,
        ),
    })


# ============================================================
# 3. ÉVÉNEMENTS PUBLICS
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def evenements_mobile(request):

    evenements = (
        Evenement.objects
        .filter(
            statut__in=["publie", "ouvert"],
            frais_billetterie_payes=True,
        )
        .select_related("createur")
        .order_by("date_evenement")[:100]
    )

    resultat = []

    for evenement in evenements:

        resultat.append({
            "id": evenement.pk,
            "titre": evenement.titre,
            "description": evenement.description,
            "lieu": evenement.lieu,
            "ville": evenement.ville,
            "pays": evenement.pays,
            "date_evenement": (
                evenement.date_evenement.isoformat()
            ),
            "prix": str(evenement.prix),
            "devise": evenement.devise,
            "nombre_places": evenement.nombre_places,
            "talent": (
                evenement.createur.get_username()
            ),
        })

    return Response({
        "evenements": resultat,
    })


# ============================================================
# 4. DÉCONNEXION MOBILE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deconnexion_mobile(request):

    # Invalide le jeton utilisé par ce compte.
    # Dans cette première version, il y a un jeton
    # partagé par utilisateur : la déconnexion
    # invalide donc aussi les autres appareils.

    if request.auth is not None:
        request.auth.delete()

    return Response({
        "message": "Déconnexion effectuée."
    })
