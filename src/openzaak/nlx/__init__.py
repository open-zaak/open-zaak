import requests
from zgw_consumers.models import Service


def fetcher(url: str, *args, **kwargs):
    """
    Fetch the URL using requests. If NLX inway is configured, rewrite absolute url to nlx url
    """
    service = Service.get_service(url)
    if service and service.nlx:
        # rewrite url
        url = url.replace(service.api_root, service.nlx, 1)

    return requests.get(url, *args, **kwargs)
