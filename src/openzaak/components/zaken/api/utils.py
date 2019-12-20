import logging

import requests
from vng_api_common.models import APICredential

logger = logging.getLogger(__name__)


def create_remote_zaakbesluit(besluit_url: str, zaak_url: str) -> dict:
    client_auth = APICredential.get_auth(zaak_url)
    if client_auth is None:
        logger.warning("Missing credentials for %s", zaak_url)

    list_url = f"{zaak_url}/besluiten"
    headers = client_auth.credentials() if client_auth else {}
    body = {"besluit": besluit_url}

    response = requests.post(list_url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


def delete_remote_zaakbesluit(zaakbesluit_url: str) -> None:
    client_auth = APICredential.get_auth(zaakbesluit_url)
    if client_auth is None:
        logger.warning("Missing credentials for %s", zaakbesluit_url)
    headers = client_auth.credentials() if client_auth else {}

    response = requests.delete(zaakbesluit_url, headers=headers)
    response.raise_for_status()
