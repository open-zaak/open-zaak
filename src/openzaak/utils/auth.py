import logging

from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


def get_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth_header = Service.get_auth_header(url)

    if auth_header is not None:
        return auth_header

    logger.warning("Could not authenticate for %s", url)
    return {}
