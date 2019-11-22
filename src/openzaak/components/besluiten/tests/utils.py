from django.conf import settings

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
