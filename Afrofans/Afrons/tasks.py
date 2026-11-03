from celery import shared_task

from .services_video import (
    traiter_video,
)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def traiter_video_task(
    self,
    video_id,
):
    try:
        resultat = traiter_video(
            video_id
        )

        if not resultat:
            raise RuntimeError(
                (
                    "Le traitement de la vidéo "
                    "n’a pas réussi."
                )
            )

        return {
            "succes": True,
            "video_id": video_id,
        }

    except Exception as erreur:
        raise self.retry(
            exc=erreur,
        )