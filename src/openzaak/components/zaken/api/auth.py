import logging

from vng_api_common.models import APICredential

logger = logging.getLogger(__name__)


def get_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth = APICredential.get_auth(url)
    if auth is None:
        logger.warning("Could not authenticate for %s", url)
        return {}
    return auth.credentials()
