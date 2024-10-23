# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import time
from typing import Optional

import jwt
from ape_pie import APIClient
from zgw_consumers.constants import AuthTypes


logger = logging.getLogger(__name__)

JWT_ALG = "HS256"


def get_auth(url: str) -> dict:
    from zgw_consumers.models import Service

    logger.info("Authenticating for %s", url)
    service = Service.get_service(url)

    if not service:
        logger.warning(f"No service found for {url}")
        return {}

    if service.auth_type == AuthTypes.zgw:
        payload = {
            "iss": service.client_id,
            "iat": int(time.time()),
            "client_id": service.client_id,
            "user_id": service.user_id,
            "user_representation": service.user_representation,
        }

        encoded = jwt.encode(payload, service.secret, algorithm=JWT_ALG)
        return {"Authorization": f"Bearer {encoded}"}
    elif service.auth_type == AuthTypes.api_key:
        return {service.header_key: service.header_value}

    logger.warning("Could not authenticate for %s", url)
    return {}


# TODO: remove this function (replaced by openzaak.client.get_client)?
def get_client(url: str) -> Optional[APIClient]:
    from zgw_consumers.client import build_client
    from zgw_consumers.models import Service
    from openzaak.client import NoServiceConfigured

    service = Service.get_service(url)

    if not service:
        raise NoServiceConfigured(f"{url} API should be added to Service model")

    return build_client(service, client_factory=APIClient)
