# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse

from vng_api_common.client import Client, to_internal_data
from zgw_consumers.client import build_client

from openzaak.utils.decorators import cache, cache_uuid

from .models import ReferentieLijstConfig

# Typing

JsonPrimitive = Union[str, int, float, bool]
ResultList = List[Dict[str, JsonPrimitive]]


def get_procestypen(procestype_jaar=None) -> ResultList:
    """
    Fetch a list of Procestypen.

    Results are cached for 24 hours.
    """
    key = "selectielijst:procestypen"
    if procestype_jaar:
        key = f"{key}-{procestype_jaar}"

    @cache(key, timeout=60 * 60 * 24)
    def inner():
        config = ReferentieLijstConfig.get_solo()
        client = build_client(config.service, client_factory=Client)  # type:ignore
        query_params = query_params = (
            {"jaar": procestype_jaar} if procestype_jaar else {}
        )
        return to_internal_data(client.get("procestypen", params=query_params))

    return inner()


def get_resultaten(proces_type: Optional[str] = None) -> ResultList:
    """
    Fetch the Selectielijst resultaten

    Optionally filtered by a procestype URL.

    Results are cached for 24 hours.
    """
    key = "selectielijst:resultaten"
    if proces_type:
        uuid = proces_type.split("/")[-1]
        key = f"{key}:pt-{uuid}"

    @cache(key, timeout=60 * 60 * 24)
    def inner():
        query_params = {}
        if proces_type:
            query_params["procesType"] = proces_type

        config = ReferentieLijstConfig.get_solo()
        client = build_client(config.service, client_factory=Client)  # type:ignore
        result_list = to_internal_data(client.get("resultaten", params=query_params))
        results = result_list["results"]
        while result_list["next"]:
            parsed = urlparse(result_list["next"])
            query = parse_qs(parsed.query)
            result_list = to_internal_data(client.get("resultaten", params=query))
            results += result_list["results"]
        return results

    return inner()


@cache("referentielijsten:resultaattypeomschrijvinggeneriek", timeout=60 * 60)
def get_resultaattype_omschrijvingen() -> ResultList:
    """
    Fetch a list of generic resultaattype omschrijvingen.

    Results are cached for an hour.
    """
    config = ReferentieLijstConfig.get_solo()
    client = build_client(config.service, client_factory=Client)  # type:ignore
    return to_internal_data(client.get("resultaattypeomschrijvingen"))


@cache_uuid("selectielijst:procestypen", timeout=60 * 60 * 24)
def retrieve_procestype(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a procestype.

    Results are cached for 24 hours.
    """
    config = ReferentieLijstConfig.get_solo()
    client = build_client(config.service, client_factory=Client)  # type:ignore
    return to_internal_data(client.get(url))


@cache_uuid("selectielijst:resultaten", timeout=60 * 60 * 24)
def retrieve_resultaat(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a resultaat

    Results are cached for 24 hours.
    """
    config = ReferentieLijstConfig.get_solo()
    client = build_client(config.service, client_factory=Client)  # type:ignore
    return to_internal_data(client.get(url))


@cache_uuid("referentielijsten:resultaattypeomschrijvinggeneriek", timeout=60 * 60)
def retrieve_resultaattype_omschrijvingen(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a generic resultaattype omschrijvingen

    Results are cached for an hours.
    """
    config = ReferentieLijstConfig.get_solo()
    client = build_client(config.service, client_factory=Client)  # type:ignore
    return to_internal_data(client.get(url))
