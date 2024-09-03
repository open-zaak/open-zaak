# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
from ape_pie import APIClient
from zgw_consumers.models import Service


class NoServiceConfigured(RuntimeError):
    pass


def fetch_object(url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    client = Service.get_client(url)
    if not client:
        raise NoServiceConfigured(f"{url} API should be added to Service model")
    return client.request(url=url, method="GET")


class OpenZaakClient(APIClient):
    pass
