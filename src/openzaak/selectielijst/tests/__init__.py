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
    return config.api_root


def mock_selectielijst_oas_get(m: Mocker) -> None:
    base_url = _get_base_url()
    mock_service_oas_get(m, url=base_url, service="selectielijst")
    mock_service_oas_get(
        m, url="", service="selectielijst", oas_url=settings.REFERENTIELIJSTEN_API_SPEC
    )


def mock_resource_list(
    m: Mocker, resource: str, query_map: Optional[dict] = None
) -> None:
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

    with open(file, "r") as response_data:
        content = json.load(response_data)
        # for paginated resources
        if isinstance(content, dict):
            content = content["results"]

    for record in content:
        if record["url"] == url:
            m.get(url, json=record)
            return

    raise MockException(f"{url} is not found in the file {file}")
