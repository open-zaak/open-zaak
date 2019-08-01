from django.apps import AppConfig


class SyncConfig(AppConfig):
    name = 'openzaak.zrc.sync'
    label = 'zrc_sync'

    def ready(self):
        from . import signals  # noqa
