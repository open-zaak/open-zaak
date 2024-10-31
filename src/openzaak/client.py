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

        # assert response_json
        return response_json

    # def head(self, url, **kwargs) -> dict | list | None:
    #     return super().head(url, **kwargs)

    # def options(self, url, **kwargs) -> dict | list | None:
    #     return super().options(url, **kwargs)

    # def get(self, url, **kwargs) -> dict | list | None:
    #     return super().get(url, **kwargs)

    # def post(self, url, **kwargs) -> dict | list | None:
    #     data = kwargs.pop("data", None)
    #     return super().post(url, {"json": data, **kwargs})

    # def put(self, url, **kwargs) -> dict | list | None:
    #     data = kwargs.pop("data", None)
    #     return super().put(url, {"json": data, **kwargs})

    # def patch(self, url, **kwargs) -> dict | list | None:
    #     data = kwargs.pop("data", None)
    #     return super().patch(url, {"json": data, **kwargs})

    # def delete(self, url, **kwargs) -> dict | list | None:
    #     return super().delete(url, **kwargs)


def get_client(
    url: str, raise_exceptions: bool = True, **client_kwargs
) -> Optional[OpenZaakClient]:
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
