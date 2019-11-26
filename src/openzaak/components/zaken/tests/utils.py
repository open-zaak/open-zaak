from datetime import datetime

from django.conf import settings
from django.utils import timezone

from vng_api_common.tests import get_operation_url as _get_operation_url

ZAAK_READ_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326"}

ZAAK_WRITE_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326", "HTTP_CONTENT_CRS": "EPSG:4326"}


def utcdatetime(*args, **kwargs) -> datetime:
    return datetime(*args, **kwargs).replace(tzinfo=timezone.utc)


def isodatetime(*args, **kwargs) -> str:
    dt = utcdatetime(*args, **kwargs)
    return dt.isoformat()


def get_operation_url(operation, **kwargs):
    return _get_operation_url(operation, spec_path=settings.SPEC_URL["zaken"], **kwargs)


def get_zaaktype_response(catalogus: str, zaaktype: str) -> dict:
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
        "selectielijstProcestype": "https://referentielijsten-api.vng.cloud/api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        "referentieproces": {},
        "statustypen": [],
        "resultaattypen": [],
        "eigenschappen": [],
        "informatieobjecttypen": [],
        "roltypen": [],
        "besluittypen": [],
        "gerelateerdeZaaktypen": [],
        "beginGeldigheid": "2019-11-20",
        "versiedatum": "2019-11-20",
        "concept": False,
    }
