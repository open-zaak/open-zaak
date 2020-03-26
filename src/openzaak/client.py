"""
Provide utilities to interact with other APIs as a client.
"""
from zgw_consumers.models import Service


def fetch_object(resource: str, url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    client = Service.get_client(url)
    obj = client.retrieve(resource, url=url)
    return obj
