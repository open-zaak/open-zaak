import logging

import requests
from vng_api_common.models import APICredential

logger = logging.getLogger(__name__)


def _get_oio_endpoint(io_url: str) -> str:
    start = io_url.split("enkelvoudiginformatieobjecten")[0]
    url = f"{start}objectinformatieobjecten"
    return url


def create_remote_oio(io_url: str, zaak_url: str) -> dict:
    client_auth = APICredential.get_auth(io_url)
    if client_auth is None:
        logger.warning("Missing credentials for %s", io_url)

    url = _get_oio_endpoint(io_url)
    headers = client_auth.credentials() if client_auth else {}
    body = {"informatieobject": io_url, "object": zaak_url, "objectType": "zaak"}

    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()
