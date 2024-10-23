# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
import logging

from ape_pie import APIClient
from requests import JSONDecodeError, RequestException, Response
from zgw_consumers.client import build_client
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


class NoServiceConfigured(RuntimeError):
    pass


def fetch_object(url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    service = Service.get_service(url)

    if not service:
        raise NoServiceConfigured(f"{url} API should be added to Service model")

    client: APIClient = build_client(service, client_factory=APIClient)

    with client:
        response: Response = client.request(method="GET", url=url)

    try:
        response.raise_for_status()
    except RequestException:
        logger.exception(f"Failed retrieving {url}")
        raise

    try:
        return response.json()
    except JSONDecodeError:
        logger.exception(f"Failed decoding json from response for {url}")
        raise
