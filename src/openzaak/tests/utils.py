import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "schemas",)

NRC_API_SPEC = os.path.join(MOCK_FILES_DIR, "nrc.yaml")


def mock_nrc_oas_get(m: Mocker) -> None:
    oas_url = "https://notificaties-api.vng.cloud/api/v1/schema/openapi.yaml?v=3"
    with open(NRC_API_SPEC, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())
