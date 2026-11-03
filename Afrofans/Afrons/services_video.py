import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.db.models import F
from django.utils import timezone

from .models import Musique, Video


class ErreurTraitementVideo(Exception):
    """
    Erreur contrôlée pendant le traitement FFmpeg.
    """

    pass


# =========================================================
# FILTRES VISUELS AFROFANS
# =========================================================

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


# =========================================================
# VÉRIFICATION DES PROGRAMMES
# =========================================================

def verifier_ffmpeg():
    """
    Vérifie que FFmpeg et FFprobe sont accessibles.
    """

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    if not ffmpeg:
        raise ErreurTraitementVideo(
            (
                "FFmpeg est introuvable. "
                "Ajoute son dossier bin au PATH Windows."
            )
        )

    if not ffprobe:
        raise ErreurTraitementVideo(
            (
                "FFprobe est introuvable. "
                "Ajoute son dossier bin au PATH Windows."
            )
        )

    return ffmpeg, ffprobe


def executer_commande(commande):
    """
    Exécute une commande FFmpeg ou FFprobe
    sans utiliser shell=True.
    """

    resultat = subprocess.run(
        commande,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )

    if resultat.returncode != 0:
        erreur = (
            resultat.stderr
            or resultat.stdout
            or "Le traitement FFmpeg a échoué."
        )

        raise ErreurTraitementVideo(
            erreur[-5000:]
        )

    return resultat


# =========================================================
# INFORMATIONS DU FICHIER VIDÉO
# =========================================================

def obtenir_informations_media(
    chemin_fichier,
):
    """
    Obtient la durée de la vidéo et vérifie
    si elle possède une piste audio.
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
        commande
    )

    try:
        informations = json.loads(
            resultat.stdout
        )

    except json.JSONDecodeError as erreur:
        raise ErreurTraitementVideo(
            (
                "FFprobe a retourné des "
                "informations invalides."
            )
        ) from erreur

    duree = float(
        informations.get(
            "format",
            {},
        ).get(
            "duration",
            0,
        )
        or 0
    )

    contient_video = any(
        flux.get("codec_type") == "video"
        for flux in informations.get(
            "streams",
            [],
        )
    )

    contient_audio = any(
        flux.get("codec_type") == "audio"
        for flux in informations.get(
            "streams",
            [],
        )
    )

    if not contient_video:
        raise ErreurTraitementVideo(
            (
                "Le fichier sélectionné ne contient "
                "aucune piste vidéo."
            )
        )

    if duree <= 0:
        raise ErreurTraitementVideo(
            (
                "La durée de la vidéo ne peut "
                "pas être déterminée."
            )
        )

    return {
        "duree": duree,
        "contient_audio": contient_audio,
    }


# =========================================================
# CONSTRUCTION DES FILTRES VISUELS
# =========================================================

def construire_filtre_video(video):
    """
    Construit les filtres vidéo selon les réglages
    choisis dans AfroFans Studio.
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
            "scale="
            "1080:1920:"
            "force_original_aspect_ratio=decrease"
        ),
        (
            "pad="
            "1080:1920:"
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

    return ",".join(
        filtres
    )


# =========================================================
# CONSTRUCTION DE LA COMMANDE FFMPEG
# =========================================================

def construire_commande_ffmpeg(
    video,
    chemin_entree,
    chemin_sortie,
):
    """
    Construit la commande complète pour intégrer
    les filtres et la musique.
    """

    ffmpeg, _ = verifier_ffmpeg()

    informations = obtenir_informations_media(
        chemin_entree
    )

    duree = informations["duree"]

    contient_audio_original = informations[
        "contient_audio"
    ]

    volume_original = max(
        0,
        min(
            1,
            float(video.volume_original)
            / 100,
        ),
    )

    volume_musique = max(
        0,
        min(
            1,
            float(video.volume_musique)
            / 100,
        ),
    )

    filtre_video = construire_filtre_video(
        video
    )

    musique_disponible = bool(
        video.musique_id
        and video.musique
        and video.musique.fichier
        and video.volume_musique > 0
    )

    chemin_musique = None

    if musique_disponible:
        try:
            chemin_musique = Path(
                video.musique.fichier.path
            )

        except (AttributeError, ValueError) as erreur:
            raise ErreurTraitementVideo(
                (
                    "Le fichier de la musique "
                    "n’est pas accessible."
                )
            ) from erreur

        if not chemin_musique.exists():
            raise ErreurTraitementVideo(
                (
                    "Le fichier musical sélectionné "
                    "n’existe pas sur le disque."
                )
            )

    commande = [
        ffmpeg,
        "-y",
        "-i",
        str(chemin_entree),
    ]

    if musique_disponible:
        commande.extend(
            [
                "-stream_loop",
                "-1",
                "-i",
                str(chemin_musique),
            ]
        )

    filtres_complexes = [
        f"[0:v]{filtre_video}[video]"
    ]

    sortie_audio = False

    # =====================================================
    # MUSIQUE + SON ORIGINAL
    # =====================================================

    if musique_disponible:

        debut_fondu = max(
            duree - 0.7,
            0,
        )

        # FFmpeg 9 exige d=0.7 et non d=.7.
        filtres_complexes.append(
            (
                "[1:a]"
                f"volume={volume_musique:.3f},"
                f"atrim=start=0:end={duree:.3f},"
                "asetpts=PTS-STARTPTS,"
                "afade="
                "type=out:"
                f"start_time={debut_fondu:.3f}:"
                "duration=0.7"
                "[musique]"
            )
        )

        if contient_audio_original:

            filtres_complexes.append(
                (
                    "[0:a]"
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

    # =====================================================
    # SON ORIGINAL SEULEMENT
    # =====================================================

    elif contient_audio_original:

        filtres_complexes.append(
            (
                "[0:a]"
                f"volume={volume_original:.3f},"
                "asetpts=PTS-STARTPTS"
                "[audio]"
            )
        )

        sortie_audio = True

    commande.extend(
        [
            "-filter_complex",
            ";".join(
                filtres_complexes
            ),
            "-map",
            "[video]",
        ]
    )

    if sortie_audio:
        commande.extend(
            [
                "-map",
                "[audio]",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
            ]
        )

    else:
        commande.append(
            "-an"
        )

    commande.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            "-t",
            f"{duree:.3f}",
            str(chemin_sortie),
        ]
    )

    return commande


# =========================================================
# ENREGISTREMENT DES ERREURS
# =========================================================

def enregistrer_echec(
    video,
    erreur,
):
    """
    Enregistre la vraie erreur FFmpeg dans la vidéo.
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


# =========================================================
# TRAITEMENT PRINCIPAL
# =========================================================

def traiter_video(video_id):
    """
    Ajoute la musique et les filtres à une vidéo.
    Retourne True en cas de succès et False
    en cas d’échec.
    """

    try:
        video = (
            Video.objects
            .select_related(
                "musique",
            )
            .get(
                pk=video_id
            )
        )

    except Video.DoesNotExist:
        return False

    # La vidéo est récupérée avant la vérification
    # de FFmpeg afin de pouvoir enregistrer l’erreur.
    video.statut_traitement = "traitement"
    video.erreur_traitement = ""

    video.save(
        update_fields=[
            "statut_traitement",
            "erreur_traitement",
            "modifiee_le",
        ]
    )

    try:
        verifier_ffmpeg()

        if not video.fichier:
            raise ErreurTraitementVideo(
                "La vidéo originale est introuvable."
            )

        try:
            chemin_entree = Path(
                video.fichier.path
            )

        except (AttributeError, ValueError) as erreur:
            raise ErreurTraitementVideo(
                (
                    "Le fichier vidéo original "
                    "n’est pas accessible."
                )
            ) from erreur

        if not chemin_entree.exists():
            raise ErreurTraitementVideo(
                (
                    "Le fichier vidéo original "
                    "n’existe pas sur le disque."
                )
            )

        with tempfile.TemporaryDirectory(
            prefix="afrofans_video_"
        ) as dossier_temporaire:

            dossier = Path(
                dossier_temporaire
            )

            chemin_sortie = (
                dossier
                / f"afrofans-{video.pk}.mp4"
            )

            commande = construire_commande_ffmpeg(
                video=video,
                chemin_entree=chemin_entree,
                chemin_sortie=chemin_sortie,
            )

            executer_commande(
                commande
            )

            if (
                not chemin_sortie.exists()
                or chemin_sortie.stat().st_size == 0
            ):
                raise ErreurTraitementVideo(
                    (
                        "FFmpeg n’a produit aucun "
                        "fichier vidéo."
                    )
                )

            ancien_fichier = (
                video.fichier_traite.name
                if video.fichier_traite
                else None
            )

            with chemin_sortie.open(
                "rb"
            ) as fichier_resultat:

                video.fichier_traite.save(
                    (
                        f"afrofans-"
                        f"{video.pk}.mp4"
                    ),
                    File(
                        fichier_resultat
                    ),
                    save=False,
                )

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

            if (
                ancien_fichier
                and ancien_fichier
                != video.fichier_traite.name
            ):
                video.fichier_traite.storage.delete(
                    ancien_fichier
                )

        if video.musique_id:
            Musique.objects.filter(
                pk=video.musique_id
            ).update(
                nombre_utilisations=(
                    F("nombre_utilisations")
                    + 1
                )
            )

        return True

    except Exception as erreur:
        enregistrer_echec(
            video,
            erreur,
        )

        return False