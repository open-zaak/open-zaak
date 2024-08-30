# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
# TODO: remove legacy import of ZGWClient
from zgw_consumers.legacy.client import ZGWClient
from zgw_consumers.models import Service


class NoServiceConfigured(RuntimeError):
    pass


def fetch_object(resource: str, url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    client = Service.get_client(url)
    if not client:
        raise NoServiceConfigured(f"{url} API should be added to Service model")
    obj = client.retrieve(resource, url=url)
    return obj


class OpenZaakClient(ZGWClient):

    @property
    def api_root(self) -> str:
        """
        work-around for libs which use new client
        """
        return self.base_url
