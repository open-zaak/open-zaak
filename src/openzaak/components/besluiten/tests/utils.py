# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
import uuid
from datetime import date

from django.conf import settings
from django.core import serializers
from django.utils import timezone

from vng_api_common.tests import get_operation_url as _get_operation_url


def get_operation_url(operation, **kwargs):
    return _get_operation_url(
        operation, spec_path=settings.SPEC_URL["besluiten"], **kwargs
    )


def get_besluittype_response(catalogus: str, besluittype: str) -> dict:
    return {
        "url": besluittype,
        "catalogus": catalogus,
        "zaaktypen": [],
        "omschrijving": "Extern Besluittype",
        "omschrijvingGeneriek": "",
        "besluitcategorie": "",
        "reactietermijn": "P14D",
        "publicatieIndicatie": True,
        "publicatietekst": "",
        "publicatietermijn": None,
        "toelichting": "",
        "informatieobjecttypen": [],
        "beginGeldigheid": "2018-01-01",
        "eindeGeldigheid": None,
        "concept": False,
    }


def get_besluit_response(besluit: str, besluittype: str, zaak: str = "") -> dict:
    return {
        "url": besluit,
        "identificatie": "BESLUIT-2019-0000000001",
        "verantwoordelijkeOrganisatie": "517439943",
        "besluittype": besluittype,
        "zaak": zaak,
        "datum": "2019-11-18",
        "toelichting": "",
        "bestuursorgaan": "",
        "ingangsdatum": "2019-11-18",
        "vervalreden": "",
        "vervalredenWeergave": "",
    }


def serialise_eio(eio, eio_url):
    serialised_eio = json.loads(serializers.serialize("json", [eio,]))[0]["fields"]
    serialised_eio = get_eio_response(eio_url, **serialised_eio)
    return serialised_eio


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
