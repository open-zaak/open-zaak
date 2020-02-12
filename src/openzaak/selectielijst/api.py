from typing import Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse

from openzaak.utils.decorators import cache, cache_uuid

from .models import ReferentieLijstConfig

# Typing

JsonPrimitive = Union[str, int, float, bool]
ResultList = List[Dict[str, JsonPrimitive]]


@cache("selectielijst:procestypen", timeout=60 * 60 * 24)
def get_procestypen() -> ResultList:
    """
    Fetch a list of Procestypen.

    Results are cached for 24 hours.
    """
    client = ReferentieLijstConfig.get_client()
    return client.list("procestype")


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

        client = ReferentieLijstConfig.get_client()
        result_list = client.list("resultaat", query_params=query_params)
        results = result_list["results"]
        while result_list["next"]:
            parsed = urlparse(result_list["next"])
            query = parse_qs(parsed.query)
            result_list = client.list("resultaat", query_params=query)
            results += result_list["results"]
        return results

    return inner()


@cache("referentielijsten:resultaattypeomschrijvinggeneriek", timeout=60 * 60)
def get_resultaattype_omschrijvingen() -> ResultList:
    """
    Fetch a list of generic resultaattype omschrijvingen.

    Results are cached for an hour.
    """
    client = ReferentieLijstConfig.get_client()
    return client.list("resultaattypeomschrijvinggeneriek")


@cache_uuid("selectielijst:procestypen", timeout=60 * 60 * 24)
def retrieve_procestype(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a procestype.

    Results are cached for 24 hours.
    """
    client = ReferentieLijstConfig.get_client()
    return client.retrieve("procestype", url)


@cache_uuid("selectielijst:resultaten", timeout=60 * 60 * 24)
def retrieve_resultaat(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a resultaat

    Results are cached for 24 hours.
    """
    client = ReferentieLijstConfig.get_client()
    return client.retrieve("resultaat", url)


@cache_uuid("referentielijsten:resultaattypeomschrijvinggeneriek", timeout=60 * 60)
def retrieve_resultaattype_omschrijvingen(url: str) -> Dict[str, JsonPrimitive]:
    """
    Fetch a generic resultaattype omschrijvingen

    Results are cached for an hours.
    """
    client = ReferentieLijstConfig.get_client()
    return client.retrieve("resultaattypeomschrijvinggeneriek", url)
