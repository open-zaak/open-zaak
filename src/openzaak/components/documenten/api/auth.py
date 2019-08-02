import logging

from vng_api_common.models import APICredential

logger = logging.getLogger(__name__)


def get_ztc_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth = APICredential.get_auth(url, scopes=['zds.scopes.zaaktypes.lezen'])
    if auth is None:
        logger.warning("Could not authenticate for %s", url)
        return {}
    return auth.credentials()


def get_zrc_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth = APICredential.get_auth(
        url,
        scopes=['zds.scopes.zaken.lezen'],
        zaaktypes=['*']
    )
    if auth is None:
        logger.warning("Could not authenticate for %s", url)
        return {}
    return auth.credentials()
