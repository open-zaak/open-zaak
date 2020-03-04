import logging

from vng_api_common.models import APICredential

from openzaak.components.autorisaties.models import ExternalAPICredential

logger = logging.getLogger(__name__)


def get_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth = APICredential.get_auth(url)
    if auth is not None:
        return auth.credentials()

    # fallback
    fallback = ExternalAPICredential.get_auth_header(url)
    if fallback:
        return fallback

    logger.warning("Could not authenticate for %s", url)
    return {}
