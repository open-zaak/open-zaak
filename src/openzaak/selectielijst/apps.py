from django.apps import AppConfig
from django.conf import settings

from zds_client import Client


class SelectielijstConfig(AppConfig):
    name = "openzaak.selectielijst"

    def ready(self):
        Client.load_config(selectielijst=settings.REFERENTIELIJSTEN_API)
