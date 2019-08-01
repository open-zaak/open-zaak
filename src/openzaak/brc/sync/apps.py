from django.apps import AppConfig


class SyncConfig(AppConfig):
    name = 'openzaak.brc.sync'
    label = 'brc_sync'

    def ready(self):
        from . import signals  # noqa
