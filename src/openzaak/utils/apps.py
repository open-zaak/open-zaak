from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'openzaak.utils'

    def ready(self):
        from . import checks  # noqa
