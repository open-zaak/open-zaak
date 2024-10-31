# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date

from django.test import TestCase, override_settings, tag
from django.urls import reverse as django_reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from rest_framework import status
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import (
    TypeCheckMixin,
    get_validation_errors,
    reverse,
    reverse_lazy,
)

from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.utils import build_absolute_url

from ...autorisaties.tests.factories import ApplicatieFactory, AutorisatieFactory
from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import (
    ConceptUpdateValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
    VerlengingsValidator,
)
from ..constants import AardRelatieChoices, InternExtern
from ..models import ZaakType, ZaakTypenRelatie
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
    ZaakTypenRelatieFactory,
)
from .utils import get_operation_url


class ZaakTypeAPITests(TypeCheckMixin, APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    def test_get_list_default_definitief(self):
        zaaktype1 = ZaakTypeFactory.create(concept=True)  # noqa
        zaaktype2 = ZaakTypeFactory.create(concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")
        zaaktype2_url = get_operation_url("zaaktype_read", uuid=zaaktype2.uuid)

        response = self.client.get(zaaktype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaaktype2_url}")

    def test_get_detail(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        zaaktype_detail_url = get_operation_url("zaaktype_read", uuid=zaaktype.uuid)

        response = self.client.get(zaaktype_detail_url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        self.assertResponseTypes(
            response_data,
            (
                ("identificatie", str),
                ("omschrijving", str),
                ("omschrijvingGeneriek", str),
                ("catalogus", str),
                ("statustypen", list),
            ),
        )
        expected = {
            "url": f"http://testserver{zaaktype_detail_url}",
            "identificatie": zaaktype.identificatie,
            "productenOfDiensten": ["https://example.com/product/123"],
            "publicatieIndicatie": zaaktype.publicatie_indicatie,
            "trefwoorden": [],
            "toelichting": "",
            "handelingInitiator": zaaktype.handeling_initiator,
            "aanleiding": zaaktype.aanleiding,
            "verlengingstermijn": None if not zaaktype.verlenging_mogelijk else "P30D",
            "opschortingEnAanhoudingMogelijk": zaaktype.opschorting_en_aanhouding_mogelijk,
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "indicatieInternOfExtern": zaaktype.indicatie_intern_of_extern,
            "verlengingMogelijk": zaaktype.verlenging_mogelijk,
            "handelingBehandelaar": zaaktype.handeling_behandelaar,
            "doel": zaaktype.doel,
            "onderwerp": zaaktype.onderwerp,
            "publicatietekst": "",
            "omschrijvingGeneriek": "",
            "vertrouwelijkheidaanduiding": "",
            "verantwoordingsrelatie": [],
            "selectielijstProcestype": zaaktype.selectielijst_procestype,
            "servicenorm": None,
            "referentieproces": {"naam": zaaktype.referentieproces_naam, "link": ""},
            "doorlooptijd": "P30D",
            "omschrijving": zaaktype.zaaktype_omschrijving,
            "eigenschappen": [],
            "informatieobjecttypen": [],
            "gerelateerdeZaaktypen": [],
            "statustypen": [],
            "resultaattypen": [],
            "roltypen": [],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "eindeGeldigheid": None,
            "versiedatum": "2018-01-01",
            "concept": True,
            "deelzaaktypen": [],
            "zaakobjecttypen": [],
            "verantwoordelijke": zaaktype.verantwoordelijke,
            "beginObject": "2018-01-01",
            "eindeObject": None,
        }
        self.assertEqual(response_data, expected)

    def test_get_detail_404(self):
        ZaakTypeFactory.create(catalogus=self.catalogus)

        url = get_operation_url("zaaktype_read", uuid=uuid.uuid4())

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        resp_data = response.json()
        del resp_data["instance"]
        self.assertEqual(
            resp_data,
            {
                "code": "not_found",
                "title": "Niet gevonden.",
                "status": 404,
                "detail": "Niet gevonden.",
                "type": "http://testserver{}".format(
                    django_reverse(
                        "vng_api_common:error-detail",
                        kwargs={"exception_class": "NotFound"},
                    )
                ),
            },
        )

    def test_create_zaaktype(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaaktype = ZaakType.objects.get(zaaktype_omschrijving="some test")

        self.assertEqual(zaaktype.catalogus, self.catalogus)
        self.assertEqual(zaaktype.besluittypen.get(), besluittype)
        self.assertEqual(zaaktype.referentieproces_naam, "ReferentieProces 0")
        self.assertEqual(
            zaaktype.zaaktypenrelaties.get().gerelateerd_zaaktype,
            "http://example.com/zaaktype/1",
        )
        self.assertEqual(zaaktype.concept, True)

    @tag("gh-1306")
    def test_create_zaaktype_identificatie_all_characters_allowed(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": "some zääktype",
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaaktype = ZaakType.objects.get(zaaktype_omschrijving="some test")

        self.assertEqual(zaaktype.catalogus, self.catalogus)
        self.assertEqual(zaaktype.besluittypen.get(), besluittype)
        self.assertEqual(zaaktype.referentieproces_naam, "ReferentieProces 0")
        self.assertEqual(
            zaaktype.zaaktypenrelaties.get().gerelateerd_zaaktype,
            "http://example.com/zaaktype/1",
        )
        self.assertEqual(zaaktype.concept, True)

    def test_create_zaaktype_referentieproces_no_link(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0"},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaaktype = ZaakType.objects.get(zaaktype_omschrijving="some test")

        self.assertEqual(zaaktype.catalogus, self.catalogus)
        self.assertEqual(zaaktype.besluittypen.get(), besluittype)
        self.assertEqual(zaaktype.referentieproces_naam, "ReferentieProces 0")
        self.assertEqual(
            zaaktype.zaaktypenrelaties.get().gerelateerd_zaaktype,
            "http://example.com/zaaktype/1",
        )
        self.assertEqual(zaaktype.concept, True)

    def test_create_zaaktype_without_verlengingstermijn(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0"},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], VerlengingsValidator.code)

    def test_create_zaaktype_generate_unique_identificatie(self):
        zaaktype1 = ZaakTypeFactory.create(catalogus=self.catalogus)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.data["identificatie"], "ZAAKTYPE-2018-0000000002")

        zaaktype2 = ZaakType.objects.get(zaaktype_omschrijving="some test")

        self.assertNotEqual(zaaktype1.identificatie, zaaktype2.identificatie)

    def test_create_zaaktype_fail_besluittype_non_concept(self):
        besluittype = BesluitTypeFactory.create(concept=False, catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptCreateValidator.code)

    def test_create_zaaktype_fail_different_catalogus_besluittypes(self):
        besluittype = BesluitTypeFactory.create()
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    def test_create_zaaktype_with_bronzaaktype(self):
        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": "ZAAK1",
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "referentieproces": {"naam": "ReferentieProces 0"},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
            "gerelateerdeZaaktypen": [],
            "besluittypen": [],
            "broncatalogus": {
                "domein": "BRON",
                "rsin": "517439943",
            },
            "bronzaaktype": {
                "identificatie": "BRONZAAK1",
                "omschrijving": "bron zaak",
            },
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaaktype = ZaakType.objects.get()

        self.assertEqual(zaaktype.broncatalogus_domein, "BRON")
        self.assertEqual(zaaktype.broncatalogus_rsin, "517439943")
        self.assertEqual(zaaktype.bronzaaktype_identificatie, "BRONZAAK1")
        self.assertEqual(zaaktype.bronzaaktype_omschrijving, "bron zaak")

    def test_create_zaaktype_with_bronzaaktype_without_broncatalogus_fail(self):
        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": "ZAAK1",
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "referentieproces": {"naam": "ReferentieProces 0"},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
            "gerelateerdeZaaktypen": [],
            "besluittypen": [],
            "bronzaaktype": {
                "identificatie": "BRONZAAK1",
                "omschrijving": "bron zaak",
            },
        }
        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-bronzaaktype-for-broncatalogus")

    def test_delete_zaaktype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = get_operation_url("zaaktype_read", uuid=zaaktype.uuid)

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.filter(id=zaaktype.id))

    def test_delete_zaaktype_fail_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = get_operation_url("zaaktype_read", uuid=zaaktype.uuid)

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-object")

    def test_delete_zaaktype_accept_header_problem_json(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = get_operation_url("zaaktype_read", uuid=zaaktype.uuid)

        response = self.client.delete(
            zaaktype_url, headers={"accept": "application/problem+json"}
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ophalen_servicenorm_doorlooptijd(self):
        zaaktype = ZaakTypeFactory.create()
        url = get_operation_url(
            "zaaktype_read", catalogus_uuid=zaaktype.catalogus.uuid, uuid=zaaktype.uuid
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertResponseTypes(
            response_data, (("doorlooptijd", str), ("servicenorm", type(None)))
        )

        self.assertEqual(response_data["doorlooptijd"], "P30D")

    def test_update_zaaktype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")

        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_update_zaaktype_with_existing_zaaktyperelatie(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype, gerelateerd_zaaktype="http://example.com/zaaktype/1"
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")

        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_update_zaaktype_with_two_existing_zaaktyperelatie(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype, gerelateerd_zaaktype="http://example.com/zaaktype/1"
        )
        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype, gerelateerd_zaaktype="http://example.com/zaaktype/2"
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")

        zaaktype.refresh_from_db()
        self.assertEqual(ZaakTypenRelatie.objects.filter(zaaktype=zaaktype).count(), 1)
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_update_zaaktype_fail_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ConceptUpdateValidator.code)

    def test_partial_update_zaaktype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")

        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_partial_update_zaaktype_fail_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)

        response = self.client.patch(zaaktype_url, {"aanleiding": "same"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ConceptUpdateValidator.code)

    def test_delete_zaaktype_not_related_to_non_concept_besluittypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(catalogus=catalogus, zaaktypen=[zaaktype])

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.filter(id=zaaktype.id).exists())

    def test_delete_zaaktype_not_related_to_non_concept_informatieobjecttypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.filter(id=zaaktype.id).exists())

    def test_delete_zaaktype_not_related_to_non_concept_zaaktypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        zaaktype2 = ZaakTypeFactory.create(catalogus=catalogus)
        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype2, gerelateerd_zaaktype=zaaktype
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.filter(id=zaaktype.id).exists())

    def test_delete_zaaktype_related_to_non_concept_besluittype_fails(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(
            catalogus=catalogus, zaaktypen=[zaaktype], concept=False
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_delete_zaaktype_related_to_non_concept_informatieobjecttype_fails(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_update_zaaktype_not_related_to_non_concept_besluittypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(catalogus=catalogus, zaaktypen=[zaaktype])

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_update_zaaktype_not_related_to_non_concept_informatieobjecttypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_update_zaaktype_not_related_to_non_concept_zaaktypen(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        zaaktype2 = ZaakTypeFactory.create(catalogus=catalogus)
        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype2, gerelateerd_zaaktype=zaaktype
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_update_zaaktype_related_to_non_concept_besluittype_fails(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(
            catalogus=catalogus, zaaktypen=[zaaktype], concept=False
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        zaaktype.delete()

    def test_update_zaaktype_related_to_non_concept_informatieobjecttype_is_allowed(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_zaaktype_add_relation_to_non_concept_besluittype_fails(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": reverse(catalogus),
            # 'informatieobjecttypen': [f'http://testserver{informatieobjecttype_url}'],
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        besluittype = BesluitTypeFactory.create(catalogus=catalogus, concept=False)
        data["besluittypen"] = [reverse(besluittype)]

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        zaaktype.delete()

    def test_partial_update_zaaktype_not_related_to_non_concept_besluittype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus, datum_einde_geldigheid="2019-01-01"
        )
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(catalogus=catalogus, zaaktypen=[zaaktype])

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_partial_update_zaaktype_not_related_to_non_concept_informatieobjecttype(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus, datum_einde_geldigheid="2019-01-01"
        )
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_partial_update_zaaktype_not_related_to_non_concept_zaaktype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus, datum_einde_geldigheid="2019-01-01"
        )
        zaaktype_url = reverse(zaaktype)

        zaaktype2 = ZaakTypeFactory.create(
            catalogus=catalogus, datum_begin_geldigheid="2020-01-01"
        )
        ZaakTypenRelatieFactory.create(
            zaaktype=zaaktype2, gerelateerd_zaaktype=zaaktype
        )

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["aanleiding"], "aangepast")
        zaaktype.delete()

    def test_partial_update_zaaktype_related_to_non_concept_informatieobjecttype_allowed(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_zaaktype_add_relation_to_non_concept_besluittype_fails(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            datum_begin_geldigheid="2018-03-01",
            versiedatum=date(2018, 3, 1),
            datum_einde_geldigheid="2019-01-01",
        )
        zaaktype_url = reverse(zaaktype)

        zaaktype_for_besluittype = ZaakTypeFactory.create(
            catalogus=catalogus,
            datum_begin_geldigheid="2015-01-01",
            versiedatum=date(2018, 3, 1),
            datum_einde_geldigheid="2016-01-01",
        )
        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, concept=False, zaaktypen=[zaaktype_for_besluittype]
        )
        data = {"besluittypen": [reverse(besluittype)]}

        response = self.client.patch(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        zaaktype.delete()

    def test_partial_update_non_concept_zaaktype_einde_geldigheid(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        response = self.client.patch(zaaktype_url, {"eindeGeldigheid": "2020-01-01"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")

    @tag("gh-981")
    def test_partial_update_non_concept_zaaktype_reset_einde_geldigheid(self):
        """
        Assert that ``null`` can be set as value for eindeGeldigheid.

        Regression test for https://github.com/open-zaak/open-zaak/issues/981
        """
        zaaktype = ZaakTypeFactory.create(
            concept=False,
            zaaktype_omschrijving="GH-981",
            identificatie="ZAAKTYPE1",
            datum_begin_geldigheid=date(2021, 1, 1),
            datum_einde_geldigheid=date(2022, 1, 1),
        )
        endpoint = reverse(zaaktype)

        with self.subTest("no overlap"):
            response = self.client.patch(endpoint, {"eindeGeldigheid": None})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            zaaktype.refresh_from_db()
            self.assertIsNone(zaaktype.datum_einde_geldigheid)

        with self.subTest("would introduce overlap"):
            zaaktype_old = ZaakTypeFactory.create(
                concept=False,
                catalogus=zaaktype.catalogus,
                zaaktype_omschrijving="GH-981",
                identificatie="ZAAKTYPE1",
                datum_begin_geldigheid=date(2020, 1, 1),
                datum_einde_geldigheid=date(2020, 12, 31),
            )

            response = self.client.patch(
                reverse(zaaktype_old), {"eindeGeldigheid": None}
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "eindeGeldigheid")
            self.assertEqual(error["code"], "overlap")

    def test_partial_update_zaaktype_einde_geldigheid_related_to_non_concept_besluittype(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(
            catalogus=catalogus, zaaktypen=[zaaktype], concept=False
        )

        response = self.client.patch(zaaktype_url, {"eindeGeldigheid": "2020-01-01"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")
        zaaktype.delete()

    def test_partial_update_zaaktype_einde_geldigheid_related_to_non_concept_informatieobjecttype(
        self,
    ):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.patch(zaaktype_url, {"eindeGeldigheid": "2020-01-01"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")
        zaaktype.delete()


class ZaakTypePublishTests(APITestCase):
    def set_realted_items(self, zaaktype):
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype,  # selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)

    def test_publish_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        self.set_realted_items(zaaktype)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaaktype.refresh_from_db()

        self.assertEqual(zaaktype.concept, False)

    def test_publish_zaaktype_with_overlapping_zaaktype(self):
        old_zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            concept=False,
            identificatie="Justin-Case",
            vertrouwelijkheidaanduiding="openbaar",
            verlenging_mogelijk=False,
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid=None,
        )

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            concept=True,
            identificatie="Justin-Case",
            vertrouwelijkheidaanduiding="openbaar",
            verlenging_mogelijk=False,
            datum_begin_geldigheid="2018-01-10",
            datum_einde_geldigheid=None,
        )
        self.set_realted_items(zaaktype)
        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "beginGeldigheid")
        self.assertEqual(error["code"], "overlap")
        self.assertEqual(
            error["reason"],
            _(
                "Dit {} komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
            ).format(ZaakType._meta.verbose_name),
        )

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

        old_zaaktype.datum_einde_geldigheid = "2018-01-09"
        old_zaaktype.save()

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

    def test_publish_zaaktype_fail_not_concept_besluittype(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        besluittype = BesluitTypeFactory.create()
        zaaktype.besluittypen.add(besluittype)
        self.set_realted_items(zaaktype)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "concept-relation")

    def test_publish_zaaktype_fail_not_concept_iotype(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        ZaakTypeInformatieObjectTypeFactory.create(zaaktype=zaaktype)
        self.set_realted_items(zaaktype)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "concept-relation")

    def test_publish_zaaktype_method_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.get(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_publish_requires_at_least_two_statustypes(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        ResultaatTypeFactory.create(zaaktype=zaaktype)
        RolTypeFactory.create(zaaktype=zaaktype)

        error_text = _(
            "Publishing a zaaktype requires at least two statustypes to be defined."
        )
        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        with self.subTest("no statustypen"):
            response = self.client.post(zaaktype_url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "statustypen")
            self.assertEqual(error["code"], "concept-relation")
            self.assertEqual(error["reason"], error_text)

        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)

        with self.subTest("one statustype"):
            response = self.client.post(zaaktype_url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "statustypen")
            self.assertEqual(error["code"], "concept-relation")
            self.assertEqual(error["reason"], error_text)

        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)

        with self.subTest("two statustype"):
            response = self.client.post(zaaktype_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            zaaktype.refresh_from_db()
            self.assertFalse(zaaktype.concept)

    def test_publish_requires_at_least_one_resultaattype(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        RolTypeFactory.create(zaaktype=zaaktype)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "resultaattypen")
        self.assertEqual(error["code"], "concept-relation")
        self.assertEqual(
            error["reason"],
            _(
                "Publishing a zaaktype requires at least one resultaattype to be defined."
            ),
        )

        ResultaatTypeFactory.create(zaaktype=zaaktype)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

    def test_publish_requires_at_least_one_roltype(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(zaaktype=zaaktype)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "roltypen")
        self.assertEqual(error["code"], "concept-relation")
        self.assertEqual(
            error["reason"],
            _("Publishing a zaaktype requires at least one roltype to be defined."),
        )

        RolTypeFactory.create(zaaktype=zaaktype)

        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

    def test_publish_multiple_errors(self):
        zaaktype = ZaakTypeFactory.create(concept=True)

        zaaktype_url = get_operation_url("zaaktype_publish", uuid=zaaktype.uuid)
        response = self.client.post(zaaktype_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        roltypen_error = get_validation_errors(response, "roltypen")
        self.assertEqual(roltypen_error["code"], "concept-relation")
        self.assertEqual(
            roltypen_error["reason"],
            _("Publishing a zaaktype requires at least one roltype to be defined."),
        )

        resultaattypen_error = get_validation_errors(response, "resultaattypen")
        self.assertEqual(resultaattypen_error["code"], "concept-relation")
        self.assertEqual(
            resultaattypen_error["reason"],
            _(
                "Publishing a zaaktype requires at least one resultaattype to be defined."
            ),
        )

        statustypen_error = get_validation_errors(response, "statustypen")
        self.assertEqual(statustypen_error["code"], "concept-relation")
        self.assertEqual(
            statustypen_error["reason"],
            _("Publishing a zaaktype requires at least two statustypes to be defined."),
        )


class ZaakTypeCreateDuplicateTests(APITestCase):
    """
    Test the creation business rules w/r to duplicates.

    A Zaaktype with the same code is allowed IF and ONLY IF it does not overlap
    in validity period.
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.catalogus = CatalogusFactory.create()

        cls.url = get_operation_url("zaaktype_list")

    def test_overlap_specified_dates(self):
        """
        Always creates concept, should not overlap
        """
        ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie=1,
            datum_begin_geldigheid=date(2019, 1, 1),
            datum_einde_geldigheid=date(2020, 1, 1),
            zaaktype_omschrijving="zaaktype",
        )

        data = {
            "omschrijving": "zaaktype",
            "identificatie": 1,
            "catalogus": f"http://testserver{reverse(self.catalogus)}",
            "beginGeldigheid": "2019-02-01",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "doel": "doel",
            "aanleiding": "aanleiding",
            "indicatieInternOfExtern": "extern",
            "handelingInitiator": "aanvragen",
            "onderwerp": "dummy",
            "handelingBehandelaar": "behandelen",
            "doorlooptijd": "P7D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": False,
            "publicatieIndicatie": False,
            "productenOfDiensten": [],
            "referentieproces": {"naam": "ref"},
            "besluittypen": [],
            "gerelateerdeZaaktypen": [],
            "versiedatum": "2019-02-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_overlap_open_end_date(self):
        """
        Always creates concept, should not overlap
        """
        ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie=1,
            datum_begin_geldigheid=date(2019, 1, 1),
            datum_einde_geldigheid=None,
            zaaktype_omschrijving="zaaktype",
        )

        data = {
            "omschrijving": "zaaktype",
            "identificatie": 1,
            "catalogus": f"http://testserver{reverse(self.catalogus)}",
            "beginGeldigheid": "2019-02-01",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "doel": "doel",
            "aanleiding": "aanleiding",
            "indicatieInternOfExtern": "extern",
            "handelingInitiator": "aanvragen",
            "onderwerp": "dummy",
            "handelingBehandelaar": "behandelen",
            "doorlooptijd": "P7D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": False,
            "publicatieIndicatie": False,
            "productenOfDiensten": [],
            "referentieproces": {"naam": "ref"},
            "besluittypen": [],
            "gerelateerdeZaaktypen": [],
            "versiedatum": "2019-02-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_no_overlap(self):
        ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie=1,
            datum_begin_geldigheid=date(2019, 1, 1),
            datum_einde_geldigheid=date(2020, 1, 1),
            zaaktype_omschrijving="zaaktype",
        )

        data = {
            "omschrijving": "zaaktype",
            "identificatie": 1,
            "catalogus": f"http://testserver{reverse(self.catalogus)}",
            "beginGeldigheid": "2020-02-01",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "doel": "doel",
            "aanleiding": "aanleiding",
            "indicatieInternOfExtern": "extern",
            "handelingInitiator": "aanvragen",
            "onderwerp": "dummy",
            "handelingBehandelaar": "behandelen",
            "doorlooptijd": "P7D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": False,
            "publicatieIndicatie": False,
            "productenOfDiensten": [],
            "referentieproces": {"naam": "ref", "link": "https://example.com"},
            "besluittypen": [],
            "gerelateerdeZaaktypen": [],
            "versiedatum": "2020-02-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ZaakTypeFilterAPITests(APITestCase):
    maxDiff = None
    url = reverse_lazy("zaaktype-list")

    def test_filter_zaaktype_status_alles(self):
        ZaakTypeFactory.create(concept=True)
        ZaakTypeFactory.create(concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")

        response = self.client.get(zaaktype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_zaaktype_status_concept(self):
        zaaktype1 = ZaakTypeFactory.create(concept=True)
        ZaakTypeFactory.create(concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")
        zaaktype1_url = get_operation_url("zaaktype_read", uuid=zaaktype1.uuid)

        response = self.client.get(zaaktype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaaktype1_url}")

    def test_filter_zaaktype_status_definitief(self):
        ZaakTypeFactory.create(concept=True)
        zaaktype2 = ZaakTypeFactory.create(concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")
        zaaktype2_url = get_operation_url("zaaktype_read", uuid=zaaktype2.uuid)

        response = self.client.get(zaaktype_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaaktype2_url}")

    def test_filter_identificatie(self):
        zaaktype1 = ZaakTypeFactory.create(concept=False, identificatie=123)
        ZaakTypeFactory.create(concept=False, identificatie=456)
        zaaktype_list_url = get_operation_url("zaaktype_list")
        zaaktype1_url = get_operation_url("zaaktype_read", uuid=zaaktype1.uuid)

        response = self.client.get(zaaktype_list_url, {"identificatie": 123})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaaktype1_url}")

    def test_filter_trefwoorden(self):
        zaaktype1 = ZaakTypeFactory.create(
            concept=False, trefwoorden=["some", "key", "words"]
        )
        ZaakTypeFactory.create(concept=False, trefwoorden=["other", "words"])
        zaaktype_list_url = get_operation_url("zaaktype_list")
        zaaktype1_url = get_operation_url("zaaktype_read", uuid=zaaktype1.uuid)

        response = self.client.get(zaaktype_list_url, {"trefwoorden": "key"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaaktype1_url}")

    def test_validate_unknown_query_params(self):
        ZaakTypeFactory.create_batch(2)
        url = reverse(ZaakType)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_filter_geldigheid(self):
        zaaktype = ZaakTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            concept=False,
        )
        ZaakTypeFactory.create(datum_begin_geldigheid=date(2020, 2, 1), concept=False)

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaaktype)}")


class ZaakTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        ZaakTypeFactory.create_batch(2, concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")

        response = self.client.get(zaaktype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakTypeFactory.create_batch(2, concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")

        response = self.client.get(zaaktype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        ZaakTypeFactory.create_batch(10, concept=False)
        zaaktype_list_url = get_operation_url("zaaktype_list")

        response = self.client.get(zaaktype_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{zaaktype_list_url}?page=2&pageSize=5"
        )


class ZaaktypeValidationTests(SelectieLijstMixin, APITestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.catalogus = CatalogusFactory.create()

        cls.url = get_operation_url("zaaktype_list")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @requests_mock.Mocker()
    def test_selectielijstprocestype_invalid_resource(self, m):
        mock_selectielijst_oas_get(m)
        procestype_url = "https://example.com/procestypen/1234"
        m.get(procestype_url, json={"some": "incorrect property"})
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url("besluittype_read", uuid=besluittype.uuid)
        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "selectielijstProcestype": procestype_url,
        }

        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "selectielijstProcestype")
        self.assertEqual(error["code"], "invalid-resource")


class ZaaktypeDeleteAutorisatieTests(TestCase):
    def test_delete_zaaktype_deletes_autorisatie(self):
        applicatie = ApplicatieFactory.create()
        zaaktype = ZaakTypeFactory.create()
        AutorisatieFactory.create(
            applicatie=applicatie,
            zaaktype=build_absolute_url(zaaktype.get_absolute_api_url()),
        )

        self.assertEqual(Autorisatie.objects.all().count(), 1)

        zaaktype.delete()

        self.assertEqual(Autorisatie.objects.all().count(), 0)
