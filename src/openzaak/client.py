# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
import logging
from typing import Optional

from ape_pie import APIClient
from requests import JSONDecodeError, RequestException, Response
from zgw_consumers.client import build_client
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


class NoServiceConfigured(RuntimeError):
    pass


class ClientError(RuntimeError):
    pass


class OpenZaakClient(APIClient):
    def request(
        self, method: str | bytes, url: str | bytes, *args, **kwargs
    ) -> dict | list | None:
        response: Response = super().request(method, url, *args, **kwargs)

        try:
            response_json = response.json()
        except JSONDecodeError:
            response_json = None

        try:
            response.raise_for_status()
        except RequestException as exc:
            if response.status_code >= 500:
                raise
            raise ClientError(response_json) from exc

        return response_json


def get_client(
    url: str | None = None,
    service: Service | None = None,
    raise_exceptions: bool = True,
    **client_kwargs,
) -> Optional[OpenZaakClient]:
    if not service:
        if not url:
            raise ValueError("Either `url` or `service` must be specified")
        service = Service.get_service(url)

    if not service:
        if raise_exceptions:
            raise NoServiceConfigured(f"{url} API should be added to Service model")

        return

    return build_client(service, client_factory=OpenZaakClient, **client_kwargs)


def fetch_object(url: str) -> dict | list | None:
    """
    Fetch a remote object by URL.
    """
    client: OpenZaakClient = get_client(url, raise_exceptions=True)

    with client:
        return client.get(url=url)
