# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from jsonschema import ValidationError, Validator
from jsonschema.validators import validator_for
from vng_api_common.tests import get_operation_url as _get_operation_url

ZAAK_READ_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326"}

ZAAK_WRITE_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326", "HTTP_CONTENT_CRS": "EPSG:4326"}
AUTH_JSON_SCHEMA_PATH = (
    Path(__file__).parents[3] / "tests/json_schemas/auth_context_schema.json"
)


def utcdatetime(*args, **kwargs) -> datetime:
    return datetime(*args, **kwargs).replace(tzinfo=timezone.utc)


def isodatetime(*args, **kwargs) -> str:
    dt = utcdatetime(*args, **kwargs)
    return dt.isoformat()


def get_operation_url(operation, **kwargs):
    return _get_operation_url(operation, spec_path=settings.SPEC_URL["zaken"], **kwargs)


def get_zaaktype_response(catalogus: str, zaaktype: str, **overrides) -> dict:
    return {
        "url": zaaktype,
        "catalogus": catalogus,
        "identificatie": "12345",
        "omschrijving": "Main zaaktype",
        "omschrijvingGeneriek": "",
        "vertrouwelijkheidaanduiding": "openbaar",
        "doel": "some desc",
        "aanleiding": "some desc",
        "toelichting": "",
        "indicatieInternOfExtern": "intern",
        "handelingInitiator": "indienen",
        "onderwerp": "Klacht",
        "handelingBehandelaar": "uitvoeren",
        "doorlooptijd": "P30D",
        "servicenorm": None,
        "opschortingEnAanhoudingMogelijk": False,
        "verlengingMogelijk": False,
        "verlengingstermijn": None,
        "trefwoorden": ["qwerty"],
        "publicatieIndicatie": False,
        "publicatietekst": "",
        "verantwoordingsrelatie": ["qwerty"],
        "productenOfDiensten": ["https://example.com/product/123"],
        "selectielijstProcestype": (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        ),
        "verantwoordelijke": "063308836",
        "referentieproces": {},
        "statustypen": [],
        "resultaattypen": [],
        "eigenschappen": [],
        "informatieobjecttypen": [],
        "roltypen": [],
        "deelzaaktypen": [],
        "besluittypen": [],
        "gerelateerdeZaaktypen": [],
        "zaakobjecttypen": [],
        "beginGeldigheid": "2019-11-20",
        "versiedatum": "2019-11-20",
        "concept": False,
        **overrides,
    }


def get_catalogus_response(catalogus: str, zaaktype: str) -> dict:
    return {
        "url": catalogus,
        "domein": "PUB",
        "contactpersoonBeheerTelefoonnummer": "0612345678",
        "rsin": "517439943",
        "contactpersoonBeheerNaam": "Jan met de Pet",
        "contactpersoonBeheerEmailadres": "jan@petten.nl",
        "informatieobjecttypen": [],
        "zaaktypen": [zaaktype],
        "besluittypen": [],
    }


def get_zaak_response(zaak: str, zaaktype: str) -> dict:
    return {
        "url": zaak,
        "uuid": "d781cd1b-f100-4051-9543-153b93299da4",
        "identificatie": "ZAAK-2019-0000000001",
        "bronorganisatie": "517439943",
        "omschrijving": "some zaak",
        "toelichting": "",
        "zaaktype": zaaktype,
        "registratiedatum": "2019-11-15",
        "verantwoordelijkeOrganisatie": "517439943",
        "startdatum": "2019-11-15",
        "communicatiekanaal": "",
        "productenOfDiensten": [],
        "vertrouwelijkheidaanduiding": "openbaar",
        "betalingsindicatie": "",
        "betalingsindicatieWeergave": "",
        "verlenging": {},
        "opschorting": {},
        "selectielijstklasse": "",
        "deelzaken": [],
        "relevanteAndereZaken": [],
        "eigenschappen": [],
        "kenmerken": [],
        "archiefstatus": "nog_te_archiveren",
    }


def get_zaakbesluit_response(zaak: str) -> dict:
    zaakbesluit_uuid = str(uuid.uuid4())
    return {
        "url": f"{zaak}/besluiten/{zaakbesluit_uuid}",
        "uuid": zaakbesluit_uuid,
        "besluit": f"http://testserver/api/v1/besluiten/{uuid.uuid4()}",
    }


def get_zaakinformatieobject_response(informatieobject: str, zaak: str) -> dict:
    zio_uuid = str(uuid.uuid4())
    return {
        "url": f"http://testserver/api/v1/zaakinformatieobjecten/{zio_uuid}",
        "uuid": zio_uuid,
        "informatieobject": informatieobject,
        "zaak": zaak,
    }


def get_resultaattype_response(resultaattype: str, zaaktype: str, **overrides) -> dict:
    return {
        "url": resultaattype,
        "zaaktype": zaaktype,
        "omschrijving": "some role",
        "resultaattypeomschrijving": (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        ),
        "omschrijvingGeneriek": "Afgewezen",
        "selectielijstklasse": (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        ),
        "toelichting": "",
        "archiefnominatie": "vernietigen",
        "archiefactietermijn": "P10Y",
        "brondatumArchiefprocedure": {
            "afleidingswijze": "afgehandeld",
            "datumkenmerk": "",
            "einddatumBekend": False,
            "objecttype": "",
            "registratie": "",
        },
        "zaaktypeIdentificatie": "ZAAK1",
        "besluittypeOmschrijving": [],
        "informatieobjecttypeOmschrijving": [],
        **overrides,
    }


def get_statustype_response(statustype: str, zaaktype: str, **overrides) -> dict:
    return {
        "url": statustype,
        "omschrijving": "statustype description",
        "omschrijvingGeneriek": "",
        "statustekst": "",
        "zaaktype": zaaktype,
        "volgnummer": 1,
        "isEindstatus": False,
        "informeren": False,
        "zaaktypeIdentificatie": "ZAAK1",
        "catalogus": "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a",
        **overrides,
    }


def get_roltype_response(roltype: str, zaaktype: str):
    return {
        "url": roltype,
        "zaaktype": zaaktype,
        "omschrijving": "some role",
        "omschrijvingGeneriek": "adviseur",
        "zaaktypeIdentificatie": "ZAAK1",
    }


def get_eigenschap_response(eigenschap: str, zaaktype: str, **overrides) -> dict:
    return {
        "url": eigenschap,
        "naam": "naam",
        "definitie": "some desc",
        "specificatie": {
            "groep": "",
            "formaat": "tekst",
            "lengte": "234",
            "kardinaliteit": "23",
            "waardenverzameling": [],
        },
        "toelichting": "",
        "zaaktype": zaaktype,
        "zaaktypeIdentificatie": "ZAAK1",
        "catalogus": "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a",
        **overrides,
    }


def get_zaakobjecttype_response(
    zaakobjecttype: str, zaaktype: str, **overrides
) -> dict:
    return {
        "url": zaakobjecttype,
        "zaaktype": zaaktype,
        "zaaktypeIdentificatie": "some zaak",
        "anderObjecttype": False,
        "objecttype": "http://example.org/objecttypen/1",
        "relatieOmschrijving": "some description",
        "resultaattypen": [],
        "statustypen": [],
        "beginGeldigheid": "2022-01-01",
        "catalogus": "http://example.org/catalogussen/1",
        **overrides,
    }


# copied from Open Forms
def _get_auth_schema_validator() -> Validator:
    with AUTH_JSON_SCHEMA_PATH.open("r") as infile:
        schema = json.load(infile)
    return validator_for(schema)(schema)


auth_schema_validator = _get_auth_schema_validator()


class AuthContextAssertMixin:
    def assertValidContext(self, context):
        try:
            auth_schema_validator.validate(context)
        except ValidationError as exc:
            raise self.failureException(
                "Context is not valid according to schema"
            ) from exc
