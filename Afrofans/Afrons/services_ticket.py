from io import BytesIO

import qrcode

from django.db import transaction

from reportlab.graphics.barcode import (
    code128,
)

from reportlab.lib import colors

from reportlab.lib.pagesizes import (
    A6,
    landscape,
)

from reportlab.lib.utils import (
    ImageReader,
)

from reportlab.pdfgen import canvas

from .models import TicketEntree


@transaction.atomic
def generer_tickets_commande(
    commande,
):

    commande = (
        commande.__class__.objects
        .select_for_update()
        .select_related(
            "evenement",
            "acheteur",
        )
        .get(
            pk=commande.pk
        )
    )

    if commande.statut != "paye":

        raise ValueError(
            (
                "Les tickets sont créés "
                "uniquement après la "
                "confirmation du paiement."
            )
        )

    existants = (
        commande.tickets.count()
    )

    quantite = int(
        commande.quantite
    )

    if existants > quantite:

        raise ValueError(
            (
                "La commande possède "
                "trop de tickets."
            )
        )

    nouveaux_a_creer = (
        quantite - existants
    )

    billets_evenement = (
        commande.evenement
        .tickets_entree
        .count()
    )

    if (
        billets_evenement
        + nouveaux_a_creer
        > commande.evenement
        .nombre_places
    ):
        raise ValueError(
            (
                "Le nombre de places "
                "de l’événement serait "
                "dépassé."
            )
        )

    for numero in range(
        existants + 1,
        quantite + 1,
    ):

        TicketEntree.objects.create(
            commande=commande,
            evenement=(
                commande.evenement
            ),
            proprietaire=(
                commande.acheteur
            ),
            numero=numero,
            nom_participant=(
                commande
                .nom_participant
            ),
        )

    return list(
        commande.tickets.all()
    )


def image_qr_ticket(
    ticket,
):

    qr = qrcode.QRCode(
        version=None,
        box_size=8,
        border=2,
    )

    qr.add_data(
        ticket.contenu_qr
    )

    qr.make(
        fit=True
    )

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return buffer


def construire_pdf_ticket(
    ticket,
):

    buffer = BytesIO()

    largeur, hauteur = landscape(
        A6
    )

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            largeur,
            hauteur,
        ),
    )

    # Fond noir

    pdf.setFillColor(
        colors.HexColor(
            "#090909"
        )
    )

    pdf.rect(
        0,
        0,
        largeur,
        hauteur,
        fill=1,
        stroke=0,
    )

    # Bandeau orange

    pdf.setFillColor(
        colors.HexColor(
            "#FF8A00"
        )
    )

    pdf.rect(
        0,
        hauteur - 34,
        largeur,
        34,
        fill=1,
        stroke=0,
    )

    # Logo texte

    pdf.setFillColor(
        colors.white
    )

    pdf.setFont(
        "Helvetica-Bold",
        16,
    )

    pdf.drawString(
        18,
        hauteur - 22,
        "AfroFans — BILLET ÉVÉNEMENT",
    )

    # Événement

    pdf.setFont(
        "Helvetica-Bold",
        15,
    )

    pdf.drawString(
        18,
        hauteur - 56,
        str(
            ticket.evenement.titre
        )[:38],
    )

    pdf.setFont(
        "Helvetica",
        8,
    )

    pdf.setFillColor(
        colors.HexColor(
            "#C9C9C9"
        )
    )

    date_evenement = (
        ticket.evenement
        .date_evenement
        .strftime(
            "%d/%m/%Y à %H:%M"
        )
    )

    pdf.drawString(
        18,
        hauteur - 71,
        date_evenement,
    )

    pdf.drawString(
        18,
        hauteur - 84,
        (
            f"{ticket.evenement.lieu} "
            f"— "
            f"{ticket.evenement.ville}, "
            f"{ticket.evenement.pays}"
        ),
    )

    pdf.drawString(
        18,
        hauteur - 97,
        (
            "Participant : "
            f"{ticket.nom_participant}"
        ),
    )

    pdf.drawString(
        18,
        hauteur - 110,
        (
            f"Billet {ticket.numero}/"
            f"{ticket.commande.quantite} "
            f"— {ticket.categorie}"
        ),
    )

    # QR code

    qr_buffer = (
        image_qr_ticket(
            ticket
        )
    )

    qr_image = ImageReader(
        qr_buffer
    )

    pdf.drawImage(
        qr_image,
        largeur - 116,
        hauteur - 148,
        width=98,
        height=98,
        preserveAspectRatio=True,
    )

    # Code du billet

    pdf.setFillColor(
        colors.HexColor(
            "#FF9D1C"
        )
    )

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        18,
        55,
        ticket.code_public,
    )

    # Code-barres

    code_barres = (
        code128.Code128(
            ticket.code_public,
            barHeight=25,
            barWidth=0.65,
        )
    )

    code_barres.drawOn(
        pdf,
        18,
        20,
    )

    pdf.setFillColor(
        colors.HexColor(
            "#8E8E8E"
        )
    )

    pdf.setFont(
        "Helvetica",
        6.5,
    )

    pdf.drawRightString(
        largeur - 18,
        10,
        (
            "QR unique — validé une "
            "seule fois à l’entrée"
        ),
    )

    pdf.showPage()

    pdf.save()

    buffer.seek(0)

    return buffer