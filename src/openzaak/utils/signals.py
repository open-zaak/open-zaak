import logging
from vng_api_common.models import APICredential
from zds_client import Client, extract_params, get_operation_url

logger = logging.getLogger(__name__)


class SyncError(Exception):
    pass


def sync_create(url, resource, data, pattern_url=None):
    # Define the remote resource with which we need to interact
    client = Client.from_url(url)
    client.auth = APICredential.get_auth(url)

    params = {}
    if pattern_url:
        try:
            pattern = get_operation_url(client.schema, f'{resource}_create', pattern_only=True)
        except ValueError as exc:
            raise SyncError("Could not determine pattern of {}".format(resource)) from exc

        # The real resource URL is extracted from the ``openapi.yaml`` based on
        # the operation
        params = extract_params(pattern_url, pattern)
    try:
        response = client.create(resource, data, **params)

    except Exception as exc:
        logger.error("Could not create {}".format(resource), exc_info=1)
        raise SyncError("Could not create {}".format(resource)) from exc

    return response


def sync_delete(url, resource):
    client = Client.from_url(url)
    client.auth = APICredential.get_auth(url)
    try:
        client.delete(resource, url=url)
    except Exception as exc:
        logger.error(f"Could not delete {resource}", exc_info=1)
        raise SyncError(f"Could not delete {resource}") from exc
