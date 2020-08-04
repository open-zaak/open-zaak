# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
import os

from django.conf import settings

from requests_mock import Mocker, MockException

from ..models import ReferentieLijstConfig

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "files",)

SELECTIELIJST_API_SPEC = os.path.join(MOCK_FILES_DIR, "openapi.yaml")


def _get_base_url() -> str:
    config = ReferentieLijstConfig.get_solo()
    return config.api_root


def mock_oas_get(m: Mocker) -> None:
    base_url = _get_base_url()
    oas_url = f"{base_url}schema/openapi.yaml"
    with open(SELECTIELIJST_API_SPEC, "rb") as api_spec:
        api_spec_content = api_spec.read()
        m.get(oas_url, content=api_spec_content)
        m.get(settings.REFERENTIELIJSTEN_API_SPEC, content=api_spec_content)


def mock_resource_list(m: Mocker, resource: str) -> None:
    url = f"{_get_base_url()}{resource}"
    file = os.path.join(MOCK_FILES_DIR, f"{resource}.json")
    with open(file, "rb") as response_data:
        m.get(url, content=response_data.read())


def mock_resource_get(m: Mocker, resource: str, url: str) -> None:
    file = os.path.join(MOCK_FILES_DIR, f"{resource}.json")

    with open(file, "r") as response_data:
        content = json.load(response_data)
        # for paginated resources
        if isinstance(content, dict):
            content = content["results"]

    for procestype_data in content:
        if procestype_data["url"] == url:
            m.get(url, json=procestype_data)
            return

    raise MockException(f"{url} is not found in the file {file}")
