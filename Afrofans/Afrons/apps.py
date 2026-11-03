from django.apps import AppConfig


class AfronsConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "Afrons"

    verbose_name = "AfroFans"

    def ready(self):

        import Afrons.signals

    def ready(self):
        from . import signals_afrofans

