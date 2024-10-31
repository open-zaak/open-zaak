# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
from pathlib import Path
from typing import Optional

from django.conf import settings

from furl import furl
from requests_mock import Mocker, MockException
from zgw_consumers.test import mock_service_oas_get

from ..models import ReferentieLijstConfig

MOCK_FILES_DIR = Path(__file__).parent / "files"


def _get_base_url() -> str:
    config = ReferentieLijstConfig.get_solo()
    assert config.service
    return config.service.api_root


def mock_selectielijst_oas_get(m: Mocker) -> None:
    base_url = _get_base_url()
    mock_service_oas_get(m, url=base_url, service="selectielijst")
    mock_service_oas_get(
        m,
        url="",
        service="selectielijst",
        oas_url=settings.REFERENTIELIJSTEN_API_STANDARD.oas_url,
    )
    mock_service_oas_get(
        m,
        url="",
        service="selectielijst",
        oas_url=settings.SELECTIELIJST_API_STANDARD.oas_url,
    )


def mock_resource_list(
    m: Mocker, resource: str, query_map: Optional[dict] = None
) -> None:
    """
    Mock retrieving a list of resources.

    :arg resources: last bit of the endpoint, used in building the URL to mock and
      JSON-file to load with mock response data.
    :arg query_map: An optional mapping of filename to querystring parameters. If
      provided, query-string specific matchers are set up with the specified JSON data
      from the provided file name.

    Example::

        >>> mock_resource_list(m, "procestypen", {"procestypen-2017": {"jaar": 2017}})
        # will mock the endpoint ending with ``/procestypen?jaar=2017`` with the data
        # from ``procestypen-2017.json``.
    """
    base_url = _get_base_url()
    if not query_map:
        url = f"{base_url}{resource}"
        file = MOCK_FILES_DIR / f"{resource}.json"
        with open(file, "rb") as response_data:
            m.get(url, content=response_data.read())
    else:
        for filename, query in query_map.items():
            url = furl(f"{base_url}{resource}")
            url.set(query)
            file = MOCK_FILES_DIR / f"{filename}.json"
            with open(file, "rb") as response_data:
                m.get(str(url), content=response_data.read())


def mock_resource_get(m: Mocker, resource: str, url: str) -> None:
    file = MOCK_FILES_DIR / f"{resource}.json"

    with open(file) as response_data:
        content = json.load(response_data)
        # for paginated resources
        if isinstance(content, dict):
            content = content["results"]

    for record in content:
        if record["url"] == url:
            m.get(url, json=record)
            return

    raise MockException(f"{url} is not found in the file {file}")
