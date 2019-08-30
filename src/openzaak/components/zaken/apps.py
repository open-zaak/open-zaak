from django.apps import AppConfig


class ZakenConfig(AppConfig):
    name = "openzaak.components.zaken"

    def ready(self):
        from .sync import signals  # noqa
