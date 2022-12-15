# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date
from functools import partial
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone

from requests_mock import Mocker
from zgw_consumers.test import mock_service_oas_get

mock_brc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="brc",
    oas_url=settings.BRC_API_STANDARD.oas_url,
)
mock_drc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="drc",
    oas_url=settings.DRC_API_STANDARD.oas_url,
)
mock_zrc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="zrc",
    oas_url=settings.ZRC_API_STANDARD.oas_url,
)
mock_ztc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="ztc",
    oas_url=settings.ZTC_API_STANDARD.oas_url,
)
mock_vrc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="vrc",
    oas_url=settings.VRC_API_STANDARD.oas_url,
)
mock_cmc_oas_get = partial(
    mock_service_oas_get,
    url="",
    service="contactmomenten",
    oas_url=settings.CMC_API_STANDARD.oas_url,
)


def mock_nrc_oas_get(m: Mocker) -> None:
    oas_url = "https://notificaties-api.vng.cloud/api/v1/schema/openapi.yaml?v=3"
    mock_service_oas_get(m, url="", service="nrc", oas_url=oas_url)


class MockSchemasMixin:
    """
    Mock fetching the schema's from Github.
    """

    mocker_attr = "adapter"

    def setUp(self):
        super().setUp()

        mocker = getattr(self, self.mocker_attr)

        mock_brc_oas_get(mocker)
        mock_drc_oas_get(mocker)
        mock_zrc_oas_get(mocker)
        mock_ztc_oas_get(mocker)


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


def patch_resource_validator(func):
    patch1 = patch("openzaak.utils.validators.ResourceValidatorMixin._resolve_schema")
    patch2 = patch("openzaak.utils.validators.obj_has_shape", return_value=True)
    return patch1(patch2(func))
