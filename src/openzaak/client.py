"""
Provide utilities to interact with other APIs as a client.
"""
from zgw_consumers.client import UnknownService
from zgw_consumers.models import Service


def fetch_object(resource: str, url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    client = Service.get_client(url)
    if not client:
        raise UnknownService(f"{url} API should be added to Service model")
    obj = client.retrieve(resource, url=url)
    return obj
