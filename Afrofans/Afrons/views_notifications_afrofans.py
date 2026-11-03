from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models_notifications_afrofans import (
    NotificationOfficielleAfroFans,
)


@login_required
@require_POST
def lire_notification_officielle(
    request,
    notification_id,
):

    notification = get_object_or_404(
        NotificationOfficielleAfroFans,
        pk=notification_id,
        destinataire=request.user,
    )

    if not notification.est_lue:

        notification.est_lue = True
        notification.save(
            update_fields=["est_lue"]
        )

    return redirect(
        "Afrons:detail_evenement",
        evenement_id=notification.evenement_id,
    )