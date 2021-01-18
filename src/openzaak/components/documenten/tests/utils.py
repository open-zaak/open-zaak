# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from typing import Dict, Union

from django.conf import settings

from vng_api_common.tests import get_operation_url as _get_operation_url

JsonValue = Union[str, None, int, float]


def get_operation_url(operation, **kwargs):
    return _get_operation_url(
        operation, spec_path=settings.SPEC_URL["documenten"], **kwargs
    )


def get_oio_response(
    io_url: str, object_url: str, object_type: str = "zaak"
) -> Dict[str, JsonValue]:
    start = io_url.split("enkelvoudiginformatieobjecten")[0]
    url = f"{start}objectinformatieobjecten"
    oio = {
        "url": url,
        "informatieobject": io_url,
        "object": object_url,
        "objectType": object_type,
    }
    return oio


def get_informatieobjecttype_response(
    catalogus: str, informatieobjecttype: str
) -> dict:
    return {
        "url": informatieobjecttype,
        "catalogus": catalogus,
        "omschrijving": "some desc",
        "vertrouwelijkheidaanduiding": "openbaar",
        "beginGeldigheid": "2019-11-18",
        "concept": False,
    }


def get_catalogus_response(catalogus: str, informatieobjecttype: str) -> dict:
    return {
        "url": catalogus,
        "domein": "PUB",
        "contactpersoonBeheerTelefoonnummer": "0612345678",
        "rsin": "517439943",
        "contactpersoonBeheerNaam": "Jan met de Pet",
        "contactpersoonBeheerEmailadres": "jan@petten.nl",
        "informatieobjecttypen": [informatieobjecttype],
        "zaaktypen": [],
        "besluittypen": [],
    }
