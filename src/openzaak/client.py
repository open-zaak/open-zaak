"""
Provide utilities to interact with other APIs as a client.
"""
from django.conf import settings
from django.utils.module_loading import import_string

from vng_api_common.models import APICredential


def fetch_object(resource: str, url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    Client = import_string(settings.ZDS_CLIENT_CLASS)
    client = Client.from_url(url)
    client.auth = APICredential.get_auth(url)
    obj = client.retrieve(resource, url=url)
    return obj
