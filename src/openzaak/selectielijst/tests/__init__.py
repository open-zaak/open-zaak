import os

from django.conf import settings

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "files",)

SELECTIELIJST_API_SPEC = os.path.join(MOCK_FILES_DIR, "openapi.yaml")


def _get_base_url() -> str:
    base_url = "{scheme}://{host}/api/v1".format(**settings.REFERENTIELIJSTEN_API)
    return base_url


def mock_oas_get(m: Mocker) -> None:
    base_url = _get_base_url()
    oas_url = f"{base_url}/schema/openapi.yaml"
    with open(SELECTIELIJST_API_SPEC, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())


def mock_resource_list(m: Mocker, resource: str) -> None:
    url = f"{_get_base_url()}/{resource}"
    file = os.path.join(MOCK_FILES_DIR, f"{resource}.json")
    with open(file, "rb") as response_data:
        m.get(url, content=response_data.read())
