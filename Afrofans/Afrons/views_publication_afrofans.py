from django.contrib import messages
from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Evenement


@staff_member_required
@require_POST
@transaction.atomic
def valider_et_publier_evenement(request, evenement_id):

    evenement = get_object_or_404(
        Evenement.objects.select_for_update(),
        pk=evenement_id,
    )

    if not evenement.frais_billetterie_payes:
        return HttpResponseForbidden(
            "Publication refusée : les frais de "
            "billetterie ne sont pas confirmés."
        )

    if evenement.statut in (
        "annule",
        "termine",
        "refuse",
    ):
        return HttpResponseForbidden(
            "Cet événement ne peut pas être publié."
        )

    if evenement.statut not in ("publie", "ouvert"):

        evenement.statut = "publie"

        # Déclenche le signal après confirmation.
        evenement.save(update_fields=["statut"])

    messages.success(
        request,
        "Événement publié. Les fans recevront "
        "une notification officielle HexaQuébec."
    )

    return redirect(
        "Afrons:detail_evenement",
        evenement_id=evenement.pk,
    )