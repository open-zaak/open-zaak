from django.apps import AppConfig


class BesluitenConfig(AppConfig):
    name = 'openzaak.components.besluiten'

    def ready(self):
        from .sync import signals  # noqa
