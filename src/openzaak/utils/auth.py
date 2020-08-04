# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from typing import Optional

from zgw_consumers.client import ZGWClient
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


def get_auth(url: str) -> dict:
    logger.info("Authenticating for %s", url)
    auth_header = Service.get_auth_header(url)

    if auth_header is not None:
        return auth_header

    logger.warning("Could not authenticate for %s", url)
    return {}


def get_client(url: str) -> Optional[ZGWClient]:
    client = Service.get_client(url)
    return client
