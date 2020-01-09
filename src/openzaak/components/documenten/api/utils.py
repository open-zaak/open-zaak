import logging

from django.conf import settings

import requests
from rest_framework.reverse import reverse
from vng_api_common.models import APICredential

from openzaak.utils import build_absolute_url

logger = logging.getLogger(__name__)


# TODO: move to general purpose utils
def get_absolute_url(url_name: str, uuid: str) -> str:
    path = reverse(
        url_name,
        kwargs={"version": settings.REST_FRAMEWORK["DEFAULT_VERSION"], "uuid": uuid},
    )
    return build_absolute_url(path)


def _get_oio_endpoint(io_url: str) -> str:
    """
    Build the OIO endpoint from the EIO URL.

    .. todo: TODO: clean this mess up - ideally this would use
    gemma_zds_client.Client.from_url() & fetch the URL from the associated
    API spec, but that requires mocking out the api spec fetch + setting up
    the schema in the mock. A refactor in gemma-zds-client for this is
    suitable.
    """
    start = io_url.split("enkelvoudiginformatieobjecten")[0]
    url = f"{start}objectinformatieobjecten"
    return url


def create_remote_oio(io_url: str, object_url: str, object_type: str = "zaak") -> dict:
    client_auth = APICredential.get_auth(io_url)
    if client_auth is None:
        logger.warning("Missing credentials for %s", io_url)

    url = _get_oio_endpoint(io_url)
    headers = client_auth.credentials() if client_auth else {}
    body = {"informatieobject": io_url, "object": object_url, "objectType": object_type}

    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


def delete_remote_oio(oio_url: str) -> None:
    client_auth = APICredential.get_auth(oio_url)
    if client_auth is None:
        logger.warning("Missing credentials for %s", oio_url)
    headers = client_auth.credentials() if client_auth else {}

    response = requests.delete(oio_url, headers=headers)
    response.raise_for_status()
