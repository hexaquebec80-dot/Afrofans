from django.conf import settings
from django.core.files.storage import FileSystemStorage


class StockageVerificationPrive(FileSystemStorage):

    def __init__(self):

        super().__init__(
            location=settings.PRIVATE_VERIFICATION_ROOT,
            base_url=None,
            file_permissions_mode=0o600,
            directory_permissions_mode=0o700,
        )

    def url(self, name):
        raise ValueError(
            "Les documents de vérification "
            "ne possèdent pas d'URL publique."
        )


def stockage_documents_verification():
    return StockageVerificationPrive()