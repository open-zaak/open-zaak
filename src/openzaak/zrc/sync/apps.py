from django.apps import AppConfig


class SyncConfig(AppConfig):
    name = 'openzaak.zrc.sync'

    def ready(self):
        from . import signals  # noqa
