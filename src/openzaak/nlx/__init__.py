# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests
from zgw_consumers.client import build_client
from zgw_consumers.models import Service


def fetcher(url: str, *args, **kwargs):
    """
    Fetch the URL using requests.

    If the matching :class:`zgw_consumers.models.Service` is configured, the request is
    made with a client built from it, which takes care of rewriting the url to the NLX
    address (if configured) and of applying the (mutual) TLS certificates of the
    service, so that endpoints requiring a server and/or client certificate can be
    reached during validation. See #2313.
    """
    service = Service.get_service(url)
    if service:
        client = build_client(service)
        return client.get(url, *args, **kwargs)

    return requests.get(url, *args, **kwargs)
