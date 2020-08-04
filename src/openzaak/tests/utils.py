# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "schemas",)

NRC_API_SPEC = os.path.join(MOCK_FILES_DIR, "nrc.yaml")


_CACHE = {}


def mock_nrc_oas_get(m: Mocker) -> None:
    oas_url = "https://notificaties-api.vng.cloud/api/v1/schema/openapi.yaml?v=3"
    with open(NRC_API_SPEC, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())


def mock_service_oas_get(
    m: Mocker, service: str, url: str = None, oas_url: str = None
) -> None:
    file_name = f"{service}.yaml"
    file = os.path.join(MOCK_FILES_DIR, file_name)
    if not oas_url:
        oas_url = f"{url}schema/openapi.yaml?v=3"

    if oas_url not in _CACHE:
        with open(file, "rb") as api_spec:
            _CACHE[oas_url] = api_spec.read()

    m.get(oas_url, content=_CACHE[oas_url])
