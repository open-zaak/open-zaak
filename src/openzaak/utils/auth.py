# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from zgw_consumers.constants import AuthTypes

logger = logging.getLogger(__name__)


def get_auth(url: str) -> dict:
    from zgw_consumers.client import ServiceConfigAdapter
    from zgw_consumers.models import Service

    logger.info("Authenticating for %s", url)
    service = Service.get_service(url)

    if not service:
        logger.warning(f"No service found for {url}")
        return {}

    if service.auth_type == AuthTypes.zgw:
        auth = ServiceConfigAdapter(service).get_client_session_kwargs()["auth"]
        return {"Authorization": f"Bearer {auth._token}"}
    elif service.auth_type == AuthTypes.api_key:
        auth = ServiceConfigAdapter(service).get_client_session_kwargs()["auth"]
        return {auth.header: auth.key}

    logger.warning("Could not authenticate for %s", url)
    return {}
