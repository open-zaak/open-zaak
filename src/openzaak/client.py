# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
import logging

from vng_api_common.client import Client, get_client, to_internal_data

logger = logging.getLogger(__name__)


def fetch_object(url: str) -> dict | list | None:
    """
    Fetch a remote object by URL.
    """
    client: Client = get_client(url, raise_exceptions=True)

    with client:
        return to_internal_data(client.get(url=url))
