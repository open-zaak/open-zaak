# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "files",)

NOTIFICATIES_API_SPEC = os.path.join(MOCK_FILES_DIR, "openapi.yaml")


def mock_oas_get(m: Mocker) -> None:
    oas_url = "https://notificaties-api.vng.cloud/api/v1/schema/openapi.yaml"
    with open(NOTIFICATIES_API_SPEC, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())


def mock_notification_send(m: Mocker, **kwargs) -> None:
    endpoint = "https://notificaties-api.vng.cloud/api/v1/notificaties"
    defaults = {
        "status_code": 201,
        "json": {"dummy": "json"},
    }
    defaults.update(**kwargs)

    if "exc" in kwargs:
        defaults = kwargs

    m.post(endpoint, **defaults)
