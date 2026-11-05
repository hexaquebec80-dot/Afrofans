
# ============================================================
# AFROFANS STUDIO — SERVICE DE MONTAGE VIDÉO
# ============================================================
#
# Entreprise : HexaQuébec
# Application : AfroFans
#
# Compatible :
# - Django
# - PostgreSQL
# - Cloudinary
# - Render
# - FFmpeg 5.1+
#
# Fonctionnalités :
# - Vidéo originale
# - Musique automatique ou manuelle
# - Conservation du son original
# - Mixage audio
# - Filtres de couleurs
# - Luminosité, contraste, saturation
# - Encodage MP4
# - Stockage Cloudinary
# - Gestion des erreurs
# - Réduction de la consommation RAM
#
# ============================================================


import json
import logging
import os
import shutil
import subprocess
import tempfile

from pathlib import Path

from django.core.files import File
from django.db.models import F
from django.utils import timezone

from .models import Musique, Video


# ============================================================
# JOURNALISATION
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION DU TRAITEMENT
# ============================================================

# Résolution optimisée pour une petite instance Render.
# À augmenter uniquement avec davantage de ressources.

LARGEUR_VIDEO = 540
HAUTEUR_VIDEO = 960

# Limiter les ressources FFmpeg.

FFMPEG_THREADS = 1

# 105 secondes par défaut pour éviter de bloquer
# trop longtemps un worker Web Render.
# Peut être adapté via une variable d'environnement.

FFMPEG_TIMEOUT = int(
    os.getenv(
        "AFROFANS_FFMPEG_TIMEOUT",
        "105",
    )
)

FFPROBE_TIMEOUT = 20

# Taille maximale des fichiers temporaires copiés.
# 200 Mo par fichier.

TAILLE_MAX_FICHIER = 200 * 1024 * 1024

# Copie par morceaux de 1 Mo.

TAILLE_BLOC = 1024 * 1024


# ============================================================
# EXCEPTION PERSONNALISÉE
# ============================================================

class ErreurTraitementVideo(Exception):
    """
    Erreur contrôlée pendant le montage vidéo.
    """
    pass


# ============================================================
# FILTRES VISUELS OFFICIELS AFROFANS
# ============================================================

FILTRES_PREDEFINIS = {

    "natural": {
        "luminosite": 0,
        "contraste": 1,
        "saturation": 1,
        "extra": "",
    },

    "warm": {
        "luminosite": 0.02,
        "contraste": 1.04,
        "saturation": 1.30,
        "extra": (
            "colorbalance="
            "rs=0.08:"
            "gs=0.025:"
            "bs=-0.06"
        ),
    },

    "cinema": {
        "luminosite": -0.04,
        "contraste": 1.20,
        "saturation": 0.82,
        "extra": (
            "colorbalance="
            "rs=0.02:"
            "bs=0.05"
        ),
    },

    "vibrant": {
        "luminosite": 0.01,
        "contraste": 1.08,
        "saturation": 1.65,
        "extra": "",
    },

    "gold": {
        "luminosite": 0.03,
        "contraste": 1.08,
        "saturation": 1.40,
        "extra": (
            "colorbalance="
            "rs=0.12:"
            "gs=0.045:"
            "bs=-0.10"
        ),
    },

    "mono": {
        "luminosite": 0,
        "contraste": 1.20,
        "saturation": 0,
        "extra": "",
    },
}


# ============================================================
# 1. VÉRIFIER FFMPEG ET FFPROBE
# ============================================================

def verifier_ffmpeg():
    """
    Vérifie la disponibilité des exécutables FFmpeg
    et FFprobe sur Windows, Linux ou Render.
    """

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    if not ffmpeg:
        raise ErreurTraitementVideo(
            "FFmpeg est introuvable sur le serveur."
        )

    if not ffprobe:
        raise ErreurTraitementVideo(
            "FFprobe est introuvable sur le serveur."
        )

    return ffmpeg, ffprobe


# ============================================================
# 2. EXÉCUTER UNE COMMANDE
# ============================================================

def executer_commande(
    commande,
    timeout=None,
):
    """
    Exécute FFmpeg ou FFprobe.

    - Sans shell=True
    - Avec délai maximal
    - Avec capture des erreurs
    """

    try:

        resultat = subprocess.run(
            commande,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            shell=False,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )

    except subprocess.TimeoutExpired as erreur:

        logger.error(
            "AfroFans Studio : délai FFmpeg dépassé."
        )

        raise ErreurTraitementVideo(
            "Le traitement vidéo a dépassé "
            "le temps autorisé."
        ) from erreur

    except OSError as erreur:

        raise ErreurTraitementVideo(
            "Impossible de lancer FFmpeg."
        ) from erreur

    if resultat.returncode != 0:

        details = (
            resultat.stderr
            or resultat.stdout
            or "Erreur FFmpeg inconnue."
        )

        raise ErreurTraitementVideo(
            "Erreur FFmpeg : "
            + details[-4500:]
        )

    return resultat


# ============================================================
# 3. COPIER UN MÉDIA CLOUDINARY EN LOCAL
# ============================================================

def copier_media_en_local(
    champ_fichier,
    dossier,
    nom_fichier,
):
    """
    Copie une vidéo ou une musique vers
    un dossier temporaire.

    Compatible avec les stockages Django
    disposant d'une méthode open(), notamment
    le stockage local et les stockages distants
    qui prennent en charge la lecture.

    Aucun appel à .path.
    """

    if not champ_fichier:

        raise ErreurTraitementVideo(
            "Le fichier média est introuvable."
        )

    destination = (
        Path(dossier) / nom_fichier
    )

    taille_totale = 0

    try:

        stockage = champ_fichier.storage

        with stockage.open(
            champ_fichier.name,
            "rb",
        ) as source:

            with destination.open("wb") as sortie:

                while True:

                    bloc = source.read(
                        TAILLE_BLOC
                    )

                    if not bloc:
                        break

                    taille_totale += len(bloc)

                    if (
                        taille_totale
                        > TAILLE_MAX_FICHIER
                    ):

                        raise ErreurTraitementVideo(
                            "Le fichier dépasse la taille "
                            "maximale autorisée pour "
                            "ce traitement."
                        )

                    sortie.write(bloc)

    except ErreurTraitementVideo:
        raise

    except Exception as erreur:

        logger.exception(
            "Impossible de récupérer le média %s",
            champ_fichier.name,
        )

        raise ErreurTraitementVideo(
            "Impossible de récupérer le fichier "
            "depuis Cloudinary ou son stockage."
        ) from erreur

    if not destination.exists():

        raise ErreurTraitementVideo(
            "Le fichier temporaire n'a pas été créé."
        )

    if destination.stat().st_size == 0:

        raise ErreurTraitementVideo(
            "Le fichier récupéré est vide."
        )

    return destination


# ============================================================
# 4. INFORMATIONS D'UNE VIDÉO
# ============================================================

def obtenir_informations_media(
    chemin_fichier,
):
    """
    Analyse la vidéo avec FFprobe.

    Retourne :
    - Durée
    - Présence d'une piste vidéo
    - Présence d'une piste audio
    """

    _, ffprobe = verifier_ffmpeg()

    commande = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-show_streams",
        "-of",
        "json",
        str(chemin_fichier),
    ]

    resultat = executer_commande(
        commande,
        timeout=FFPROBE_TIMEOUT,
    )

    try:

        informations = json.loads(
            resultat.stdout
        )

    except (
        json.JSONDecodeError,
        TypeError,
    ) as erreur:

        raise ErreurTraitementVideo(
            "FFprobe a retourné des "
            "informations invalides."
        ) from erreur

    try:

        duree = float(
            informations.get(
                "format",
                {},
            ).get(
                "duration",
                0,
            ) or 0
        )

    except (
        TypeError,
        ValueError,
    ) as erreur:

        raise ErreurTraitementVideo(
            "Durée vidéo invalide."
        ) from erreur

    flux = informations.get(
        "streams",
        [],
    )

    contient_video = any(
        element.get("codec_type") == "video"
        for element in flux
    )

    contient_audio = any(
        element.get("codec_type") == "audio"
        for element in flux
    )

    if not contient_video:

        raise ErreurTraitementVideo(
            "Le fichier ne contient "
            "aucune piste vidéo."
        )

    if duree <= 0:

        raise ErreurTraitementVideo(
            "La durée de la vidéo "
            "ne peut pas être déterminée."
        )

    return {
        "duree": duree,
        "contient_audio": contient_audio,
    }


# ============================================================
# 5. CONSTRUIRE LES FILTRES VISUELS
# ============================================================

def construire_filtre_video(video):
    """
    Applique les réglages AfroFans Studio.

    Résolution réduite à 540x960
    pour diminuer la consommation RAM.
    """

    preset = FILTRES_PREDEFINIS.get(
        video.filtre_couleur,
        FILTRES_PREDEFINIS["natural"],
    )

    luminosite_utilisateur = (
        float(video.luminosite) - 100
    ) / 100

    contraste_utilisateur = (
        float(video.contraste) / 100
    )

    saturation_utilisateur = (
        float(video.saturation) / 100
    )

    luminosite = max(
        -1,
        min(
            1,
            preset["luminosite"]
            + luminosite_utilisateur,
        ),
    )

    contraste = max(
        0,
        min(
            2,
            preset["contraste"]
            * contraste_utilisateur,
        ),
    )

    saturation = max(
        0,
        min(
            3,
            preset["saturation"]
            * saturation_utilisateur,
        ),
    )

    filtres = [

        (
            f"scale={LARGEUR_VIDEO}:"
            f"{HAUTEUR_VIDEO}:"
            "force_original_aspect_ratio=decrease"
        ),

        (
            f"pad={LARGEUR_VIDEO}:"
            f"{HAUTEUR_VIDEO}:"
            "(ow-iw)/2:"
            "(oh-ih)/2:"
            "color=black"
        ),

        (
            "eq="
            f"brightness={luminosite:.3f}:"
            f"contrast={contraste:.3f}:"
            f"saturation={saturation:.3f}"
        ),
    ]

    if preset["extra"]:

        filtres.append(
            preset["extra"]
        )

    filtres.append(
        "format=yuv420p"
    )

    return ",".join(filtres)


# ============================================================
# 6. CONSTRUIRE LA COMMANDE FFMPEG
# ============================================================

def construire_commande_ffmpeg(
    video,
    chemin_entree,
    chemin_sortie,
    chemin_musique=None,
):
    """
    Prépare le montage :

    - Filtres visuels
    - Son original
    - Musique
    - Mixage audio
    - Export MP4

    chemin_musique doit être un fichier local
    temporaire, déjà copié depuis son stockage.
    """

    ffmpeg, _ = verifier_ffmpeg()

    informations = obtenir_informations_media(
        chemin_entree
    )

    duree = informations["duree"]

    contient_audio_original = (
        informations["contient_audio"]
    )

    volume_original = max(
        0,
        min(
            1,
            float(video.volume_original) / 100,
        ),
    )

    volume_musique = max(
        0,
        min(
            1,
            float(video.volume_musique) / 100,
        ),
    )

    filtre_video = construire_filtre_video(
        video
    )

    musique_disponible = bool(
        chemin_musique is not None
        and volume_musique > 0
    )

    commande = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-filter_complex_threads",
        str(FFMPEG_THREADS),
        "-i",
        str(chemin_entree),
    ]

    # ========================================================
    # AJOUTER LA MUSIQUE
    # ========================================================

    if musique_disponible:

        commande.extend([
            "-stream_loop",
            "-1",
            "-i",
            str(chemin_musique),
        ])

    filtres_complexes = [
        f"[0:v:0]{filtre_video}[video]"
    ]

    sortie_audio = False

    # ========================================================
    # MUSIQUE AVEC OU SANS SON ORIGINAL
    # ========================================================

    if musique_disponible:

        debut_fondu = max(
            duree - 0.7,
            0,
        )

        duree_fondu = min(
            0.7,
            duree,
        )

        filtres_complexes.append(
            (
                "[1:a:0]"
                f"volume={volume_musique:.3f},"
                f"atrim=start=0:end={duree:.3f},"
                "asetpts=PTS-STARTPTS,"
                "afade="
                "type=out:"
                f"start_time={debut_fondu:.3f}:"
                f"duration={duree_fondu:.3f}"
                "[musique]"
            )
        )

        if contient_audio_original:

            filtres_complexes.append(
                (
                    "[0:a:0]"
                    f"volume={volume_original:.3f},"
                    "asetpts=PTS-STARTPTS"
                    "[original]"
                )
            )

            filtres_complexes.append(
                (
                    "[original][musique]"
                    "amix="
                    "inputs=2:"
                    "duration=first:"
                    "dropout_transition=2:"
                    "normalize=0"
                    "[audio]"
                )
            )

        else:

            filtres_complexes.append(
                "[musique]anull[audio]"
            )

        sortie_audio = True

    # ========================================================
    # SON ORIGINAL UNIQUEMENT
    # ========================================================

    elif contient_audio_original:

        filtres_complexes.append(
            (
                "[0:a:0]"
                f"volume={volume_original:.3f},"
                "asetpts=PTS-STARTPTS"
                "[audio]"
            )
        )

        sortie_audio = True

    # ========================================================
    # APPLIQUER LES FILTRES
    # ========================================================

    commande.extend([
        "-filter_complex",
        ";".join(filtres_complexes),
        "-map",
        "[video]",
    ])

    # ========================================================
    # ENCODAGE AUDIO
    # ========================================================

    if sortie_audio:

        commande.extend([
            "-map",
            "[audio]",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
        ])

    else:

        commande.append("-an")

    # ========================================================
    # ENCODAGE VIDÉO OPTIMISÉ POUR RENDER
    # ========================================================

    commande.extend([
        "-c:v",
        "libx264",

        "-threads",
        str(FFMPEG_THREADS),

        "-preset",
        "ultrafast",

        "-crf",
        "28",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-movflags",
        "+faststart",

        "-t",
        f"{duree:.3f}",

        str(chemin_sortie),
    ])

    return commande


# ============================================================
# 7. ENREGISTRER UNE ERREUR
# ============================================================

def enregistrer_echec(
    video,
    erreur,
):
    """
    Enregistre l'échec dans PostgreSQL.

    La vidéo originale reste conservée.
    La publication reste privée.
    """

    video.statut_traitement = "echec"

    video.erreur_traitement = str(
        erreur
    )[:5000]

    video.est_publiee = False

    video.save(
        update_fields=[
            "statut_traitement",
            "erreur_traitement",
            "est_publiee",
            "modifiee_le",
        ]
    )


# ============================================================
# 8. TRAITEMENT PRINCIPAL AFROFANS STUDIO
# ============================================================

def traiter_video(video_id):
    """
    Traite une vidéo AfroFans.

    Étapes :

    1. Charger la vidéo depuis PostgreSQL
    2. Vérifier FFmpeg
    3. Copier la vidéo depuis Cloudinary
    4. Copier éventuellement la musique
    5. Appliquer les filtres avec FFmpeg
    6. Créer le montage MP4
    7. Enregistrer le MP4 sur Cloudinary
    8. Actualiser PostgreSQL
    9. Publier la vidéo

    Retourne :
        True  = succès
        False = échec
    """

    # ========================================================
    # 1. RÉCUPÉRER LA VIDÉO
    # ========================================================

    try:

        video = (
            Video.objects
            .select_related("musique")
            .get(pk=video_id)
        )

    except Video.DoesNotExist:

        logger.error(
            "AfroFans Studio : vidéo %s introuvable.",
            video_id,
        )

        return False

    # ========================================================
    # 2. INITIALISER LE TRAITEMENT
    # ========================================================

    video.statut_traitement = "traitement"
    video.erreur_traitement = ""
    video.est_publiee = False

    video.save(
        update_fields=[
            "statut_traitement",
            "erreur_traitement",
            "est_publiee",
            "modifiee_le",
        ]
    )

    try:

        # ====================================================
        # 3. VÉRIFIER FFMPEG
        # ====================================================

        verifier_ffmpeg()

        if not video.fichier:

            raise ErreurTraitementVideo(
                "La vidéo originale est introuvable."
            )

        logger.info(
            "AfroFans Studio : début du traitement "
            "de la vidéo %s.",
            video.pk,
        )

        # ====================================================
        # 4. DOSSIER TEMPORAIRE
        # ====================================================

        with tempfile.TemporaryDirectory(
            prefix="afrofans_video_"
        ) as dossier_temporaire:

            dossier = Path(
                dossier_temporaire
            )

            # =================================================
            # 5. TÉLÉCHARGER LA VIDÉO ORIGINALE
            # =================================================

            extension = (
                Path(video.fichier.name)
                .suffix.lower()
            )

            if extension not in (
                ".mp4",
                ".webm",
                ".mov",
            ):
                extension = ".mp4"

            chemin_entree = copier_media_en_local(
                champ_fichier=video.fichier,
                dossier=dossier,
                nom_fichier=(
                    "video_originale"
                    + extension
                ),
            )

            logger.info(
                "AfroFans Studio : vidéo %s récupérée.",
                video.pk,
            )

            # =================================================
            # 6. RÉCUPÉRER LA MUSIQUE
            # =================================================

            chemin_musique = None

            musique_disponible = bool(
                video.musique_id
                and video.musique
                and video.musique.fichier
                and video.volume_musique > 0
            )

            if musique_disponible:

                extension_musique = (
                    Path(video.musique.fichier.name)
                    .suffix.lower()
                )

                if not extension_musique:
                    extension_musique = ".mp3"

                chemin_musique = copier_media_en_local(
                    champ_fichier=video.musique.fichier,
                    dossier=dossier,
                    nom_fichier=(
                        "musique"
                        + extension_musique
                    ),
                )

                logger.info(
                    "AfroFans Studio : musique %s "
                    "récupérée pour la vidéo %s.",
                    video.musique_id,
                    video.pk,
                )

            # =================================================
            # 7. PRÉPARER LE FICHIER DE SORTIE
            # =================================================

            chemin_sortie = (
                dossier
                / f"afrofans-{video.pk}.mp4"
            )

            # =================================================
            # 8. CONSTRUIRE LA COMMANDE FFMPEG
            # =================================================

            commande = construire_commande_ffmpeg(
                video=video,
                chemin_entree=chemin_entree,
                chemin_sortie=chemin_sortie,
                chemin_musique=chemin_musique,
            )

            # =================================================
            # 9. LANCER LE MONTAGE
            # =================================================

            logger.info(
                "AfroFans Studio : lancement FFmpeg "
                "pour la vidéo %s.",
                video.pk,
            )

            executer_commande(
                commande,
                timeout=FFMPEG_TIMEOUT,
            )

            # =================================================
            # 10. VÉRIFIER LE MONTAGE
            # =================================================

            if not chemin_sortie.exists():

                raise ErreurTraitementVideo(
                    "FFmpeg n'a pas créé "
                    "la vidéo traitée."
                )

            if chemin_sortie.stat().st_size == 0:

                raise ErreurTraitementVideo(
                    "Le fichier vidéo traité est vide."
                )

            # Vérifier que le MP4 final est lisible.

            obtenir_informations_media(
                chemin_sortie
            )

            logger.info(
                "AfroFans Studio : montage terminé "
                "pour la vidéo %s.",
                video.pk,
            )

            # =================================================
            # 11. SAUVEGARDER LA VIDÉO SUR CLOUDINARY
            # =================================================

            ancien_fichier = (
                video.fichier_traite.name
                if video.fichier_traite
                else None
            )

            with chemin_sortie.open("rb") as resultat:

                video.fichier_traite.save(
                    f"afrofans-{video.pk}.mp4",
                    File(
                        resultat,
                        name=f"afrofans-{video.pk}.mp4",
                    ),
                    save=False,
                )

            # =================================================
            # 12. ENREGISTRER LE RÉSULTAT
            # =================================================

            video.statut_traitement = "termine"

            video.erreur_traitement = ""

            video.traite_le = timezone.now()

            video.est_publiee = True

            video.save(
                update_fields=[
                    "fichier_traite",
                    "statut_traitement",
                    "erreur_traitement",
                    "traite_le",
                    "est_publiee",
                    "modifiee_le",
                ]
            )

            # =================================================
            # 13. SUPPRIMER L'ANCIEN MONTAGE
            # =================================================

            if (
                ancien_fichier
                and ancien_fichier
                != video.fichier_traite.name
            ):

                try:

                    video.fichier_traite.storage.delete(
                        ancien_fichier
                    )

                except Exception:

                    logger.warning(
                        "AfroFans Studio : impossible "
                        "de supprimer l'ancien montage "
                        "de la vidéo %s.",
                        video.pk,
                        exc_info=True,
                    )

        # ====================================================
        # 14. STATISTIQUES MUSICALES
        # ====================================================

        if (
            video.musique_id
            and musique_disponible
        ):

            Musique.objects.filter(
                pk=video.musique_id
            ).update(
                nombre_utilisations=(
                    F("nombre_utilisations") + 1
                )
            )

        # ====================================================
        # 15. SUCCÈS
        # ====================================================

        logger.info(
            "AfroFans Studio : vidéo %s "
            "publiée avec succès.",
            video.pk,
        )

        return True

    # ========================================================
    # 16. GESTION DES ERREURS
    # ========================================================

    except Exception as erreur:

        logger.exception(
            "AfroFans Studio : échec du traitement "
            "de la vidéo %s.",
            video.pk,
        )

        try:

            enregistrer_echec(
                video,
                erreur,
            )

        except Exception:

            logger.exception(
                "AfroFans Studio : impossible "
                "d'enregistrer l'échec "
                "de la vidéo %s.",
                video.pk,
            )

        return False


# ============================================================
# FIN — AFROFANS STUDIO
# HEXAQUÉBEC
# ============================================================
