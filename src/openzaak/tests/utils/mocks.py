# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from requests_mock import Mocker

MOCK_FILES_DIR = Path(__file__).parent.parent / "schemas"

_CACHE = {}


def mock_nrc_oas_get(m: Mocker) -> None:
    oas_url = "https://notificaties-api.vng.cloud/api/v1/schema/openapi.yaml?v=3"
    mock_service_oas_get(m, "nrc", oas_url=oas_url)


# TODO: refactor to use zgw_consumers.test.mock_service_oas_get
def mock_service_oas_get(
    m: Mocker, service: str, url: str = "", oas_url: str = ""
) -> None:
    file_name = f"{service}.yaml"
    if not oas_url:
        oas_url = f"{url}schema/openapi.yaml?v=3"

    if oas_url not in _CACHE:
        with open(MOCK_FILES_DIR / file_name, "rb") as api_spec:
            _CACHE[oas_url] = api_spec.read()

    m.get(oas_url, content=_CACHE[oas_url])


class MockSchemasMixin:
    """
    Mock fetching the schema's from Github.
    """

    mocker_attr = "adapter"

    def setUp(self):
        super().setUp()

        mocker = getattr(self, self.mocker_attr)

        mock_service_oas_get(mocker, "brc", oas_url=settings.BRC_API_SPEC)
        mock_service_oas_get(mocker, "drc", oas_url=settings.DRC_API_SPEC)
        mock_service_oas_get(mocker, "zrc", oas_url=settings.ZRC_API_SPEC)
        mock_service_oas_get(mocker, "ztc", oas_url=settings.ZTC_API_SPEC)


def get_eio_response(url, **overrides):
    eio_type = (
        f"https://external.catalogus.nl/api/v1/informatieobjecttypen/{uuid.uuid4()}"
    )
    eio = {
        "url": url,
        "identificatie": "DOCUMENT-00001",
        "bronorganisatie": "272618196",
        "creatiedatum": date.today().isoformat(),
        "titel": "some titel",
        "auteur": "some auteur",
        "status": "",
        "formaat": "some formaat",
        "taal": "nld",
        "beginRegistratie": timezone.now().isoformat().replace("+00:00", "Z"),
        "versie": 1,
        "bestandsnaam": "",
        "inhoud": f"{url}/download?versie=1",
        "bestandsomvang": 100,
        "link": "",
        "beschrijving": "",
        "ontvangstdatum": None,
        "verzenddatum": None,
        "ondertekening": {"soort": "", "datum": None},
        "indicatieGebruiksrecht": None,
        "vertrouwelijkheidaanduiding": "openbaar",
        "integriteit": {"algoritme": "", "waarde": "", "datum": None},
        "informatieobjecttype": eio_type,
        "locked": False,
    }
    eio.update(**overrides)

    if overrides.get("_informatieobjecttype_url") is not None:
        eio["informatieobjecttype"] = overrides.get("_informatieobjecttype_url")

    return eio
