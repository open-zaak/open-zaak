# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests
from zgw_consumers.models import Service


def fetcher(url: str, *args, **kwargs):
    """
    Fetch the URL using requests.
    If the NLX address is configured, rewrite absolute url to NLX url.
    """
    service = Service.get_service(url)
    if service and service.nlx:
        # rewrite url
        url = url.replace(service.api_root, service.nlx, 1)

    return requests.get(url, *args, **kwargs)
