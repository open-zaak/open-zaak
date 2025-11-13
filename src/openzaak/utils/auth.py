# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import structlog
from zgw_consumers.constants import AuthTypes

logger = structlog.stdlib.get_logger(__name__)


def get_auth(url: str) -> dict:
    from zgw_consumers.client import ServiceConfigAdapter
    from zgw_consumers.models import Service

    logger.info("authenticating_for_url", url=url)
    service = Service.get_service(url)

    if not service:
        logger.warning("no_service_found_for_url", url=url)
        return {}

    if service.auth_type == AuthTypes.zgw:
        auth = ServiceConfigAdapter(service).get_client_session_kwargs()["auth"]
        return {"Authorization": f"Bearer {auth._token}"}
    elif service.auth_type == AuthTypes.api_key:
        auth = ServiceConfigAdapter(service).get_client_session_kwargs()["auth"]
        return {auth.header: auth.key}

    logger.debug("no_auth_configured_for_service", url=url)

    return {}
