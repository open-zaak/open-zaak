# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.test import override_settings

import requests_mock
from rest_framework import status
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ComponentTypes,
)
from vng_api_common.tests import (
    TypeCheckMixin,
    get_validation_errors,
    reverse,
    reverse_lazy,
)

from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import patch_resource_validator

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..models import ResultaatType
from .base import APITestCase
from .contants import BrondatumArchiefprocedureExampleMapping as MAPPING
from .factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    ZaakTypeFactory,
)

PROCESTYPE_URL = "http://referentielijsten.nl/procestypen/1234"
SELECTIELIJSTKLASSE_URL = "https://selectielijst.openzaak.nl/api/v1/resultaten/1234"
SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL = (
    "https://selectielijst.openzaak.nl/api/v1/resultaten/4321"
)
SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL = (
    "https://selectielijst.openzaak.nl/api/v1/resultaten/5678"
)
RESULTAATTYPEOMSCHRIJVING_URL = (
    "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
)


@override_settings(SOLO_CACHE=None)
class ResultaatTypeAPITests(SelectieLijstMixin, TypeCheckMixin, APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    list_url = reverse_lazy(ResultaatType)

    def test_get_list(self):
        ResultaatTypeFactory.create_batch(3, zaaktype__concept=False)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(len(data), 3)
        self.assertResponseTypes(
            data[0],
            (
                ("url", str),
                ("zaaktype", str),
                ("omschrijving", str),
                ("resultaattypeomschrijving", str),
                ("omschrijvingGeneriek", str),
                ("selectielijstklasse", str),
                ("toelichting", str),
                ("archiefnominatie", str),
                ("archiefactietermijn", str),
                ("brondatumArchiefprocedure", dict),
            ),
        )

    def test_get_list_default_definitief(self):
        ResultaatTypeFactory.create(zaaktype__concept=True)
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype2_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype2.uuid}
        )

        response = self.client.get(resultaattype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype2_url}")

    def test_get_detail(self):
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                resultaattypeomschrijving=resultaattypeomschrijving
            )
            url = reverse(resultaattype)
            zaaktype_url = reverse(
                "zaaktype-detail", kwargs={"uuid": resultaattype.zaaktype.uuid}
            )

            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{url}",
                "zaaktype": f"http://testserver{zaaktype_url}",
                "zaaktypeIdentificatie": resultaattype.zaaktype.identificatie,
                "omschrijving": resultaattype.omschrijving,
                "resultaattypeomschrijving": resultaattype.resultaattypeomschrijving,
                "omschrijvingGeneriek": resultaattype.omschrijving_generiek,
                "selectielijstklasse": resultaattype.selectielijstklasse,
                "toelichting": "",
                "archiefnominatie": resultaattype.archiefnominatie,
                "archiefactietermijn": "P10Y",
                "brondatumArchiefprocedure": {
                    "afleidingswijze": resultaattype.brondatum_archiefprocedure_afleidingswijze,
                    "datumkenmerk": "",
                    "einddatumBekend": False,
                    "objecttype": "",
                    "registratie": "",
                    "procestermijn": None,
                },
                "indicatieSpecifiek": None,
                "procesobjectaard": "",
                "procestermijn": None,
                "catalogus": f"http://testserver{reverse(resultaattype.zaaktype.catalogus)}",
                "informatieobjecttypen": [],
                "informatieobjecttypeOmschrijving": [],
                "besluittypen": [],
                "besluittypeOmschrijving": [],
                "beginGeldigheid": None,
                "eindeGeldigheid": None,
                "beginObject": None,
                "eindeObject": None,
            },
        )

    def test_resultaattypen_embedded_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create()
        url = f"http://testserver{reverse(resultaattype)}"
        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": resultaattype.zaaktype.uuid}
        )

        response = self.client.get(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["resultaattypen"], [url])

    def test_resultaattype_afleidingswijze_procestermijn(self):
        resultaattype = ResultaatTypeFactory.create(
            brondatum_archiefprocedure_afleidingswijze="procestermijn",
            brondatum_archiefprocedure_procestermijn="P5Y",
        )

        url = reverse(resultaattype)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        brondatumArchiefprocedure = response.json()["brondatumArchiefprocedure"]
        self.assertEqual(brondatumArchiefprocedure["afleidingswijze"], "procestermijn")
        # Verify that the procestermijn was serialized correctly
        self.assertEqual(brondatumArchiefprocedure["procestermijn"], "P5Y")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype(self, mock_shape, mock_fetch, m):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = ResultaatType.objects.get()

        self.assertEqual(resultaattype.omschrijving_generiek, "test")
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure_afleidingswijze,
            Afleidingswijze.afgehandeld,
        )
        self.assertEqual(resultaattype.datum_begin_geldigheid, date(2023, 1, 1))
        self.assertEqual(resultaattype.datum_einde_geldigheid, date(2023, 12, 1))

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_brondatum_archiefprocedure_null(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": None,
        }
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json()["brondatumArchiefprocedure"],
            {
                "afleidingswijze": "afgehandeld",
                "datumkenmerk": "",
                "einddatumBekend": False,
                "objecttype": "",
                "registratie": "",
                "procestermijn": None,
            },
        )

        resultaattype = ResultaatType.objects.get()
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure,
            {
                "afleidingswijze": "afgehandeld",
                "datumkenmerk": "",
                "einddatum_bekend": False,
                "objecttype": "",
                "registratie": "",
                "procestermijn": None,
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_brondatum_archiefprocedure_null_with_vernietigen(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "vernietigen",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": None,
        }
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_resultaattype_brondatum_archiefprocedure(self):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                brondatum_archiefprocedure_afleidingswijze=Afleidingswijze.afgehandeld,
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url, {"omschrijving": "aangepast"}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")
        self.assertEqual(
            response.data["brondatum_archiefprocedure"]["afleidingswijze"],
            Afleidingswijze.afgehandeld,
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_fail_not_concept_zaaktype(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_with_end_date_before_start_date(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "beginGeldigheid": "2023-12-01",
            "eindeGeldigheid": "2023-01-01",
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "date-mismatch")

    def test_delete_resultaattype(self):
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype.uuid}
        )

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResultaatType.objects.filter(id=resultaattype.id))

    def test_delete_resultaattype_fail_not_concept_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype.uuid}
        )

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_derive_archiefactiedatum_from_selectielijstklasse(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "bewaartermijn": "P5Y",
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["archiefactietermijn"], "P5Y")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_update_resultaattype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

            response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_update_resultaattype_fail_not_concept_zaaktype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

            response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

            response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    def test_partial_update_resultaattype(self):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                archiefnominatie="blijvend_bewaren",
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url, {"omschrijving": "aangepast"}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    def test_partial_update_resultaattype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype, archiefnominatie="blijvend_bewaren"
        )
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(resultaattype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_partial_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(archiefnominatie="vernietigen")
        resultaattype_url = reverse(resultaattype)

        with requests_mock.Mocker() as m:
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )

            response = self.client.patch(resultaattype_url, {"zaaktype": zaaktype_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_update_resultaattype_omschrijving_generiek(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse(zaaktype)

        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        with requests_mock.Mocker() as m:
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving_url,
            )
        self.assertEqual(resultaattype.omschrijving_generiek, "init")

        resultaattype_url = reverse(resultaattype)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
        }

        with requests_mock.Mocker() as m:
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})
            response = self.client.patch(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving_generiek"], "test")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_with_informatieobjecttypen(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        iotype = InformatieObjectTypeFactory.create(catalogus=zaaktype.catalogus)
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "informatieobjecttypen": [f"http://testserver{reverse(iotype)}"],
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = ResultaatType.objects.get()

        self.assertEqual(resultaattype.omschrijving_generiek, "test")
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure_afleidingswijze,
            Afleidingswijze.afgehandeld,
        )
        self.assertEqual(list(resultaattype.informatieobjecttypen.all()), [iotype])

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_with_iotype_another_catalogus_fail(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        iotype = InformatieObjectTypeFactory.create()
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "informatieobjecttypen": [f"http://testserver{reverse(iotype)}"],
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_patch_resultaattype_with_informatieobjecttypen(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        iotype = InformatieObjectTypeFactory.create(catalogus=zaaktype.catalogus)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                archiefnominatie="blijvend_bewaren",
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url,
                {"informatieobjecttypen": [f"http://testserver{reverse(iotype)}"]},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(resultaattype.informatieobjecttypen.all()), [iotype])

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_patch_resultaattype_with_iotype_another_catalogus_fail(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        iotype = InformatieObjectTypeFactory.create()
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                archiefnominatie="blijvend_bewaren",
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url,
                {"informatieobjecttypen": [f"http://testserver{reverse(iotype)}"]},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_with_besluittypen(self, mock_shape, mock_fetch, m):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        besluittype = BesluitTypeFactory.create(catalogus=zaaktype.catalogus)
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluittypen": [f"http://testserver{reverse(besluittype)}"],
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = ResultaatType.objects.get()

        self.assertEqual(resultaattype.omschrijving_generiek, "test")
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure_afleidingswijze,
            Afleidingswijze.afgehandeld,
        )
        self.assertEqual(list(resultaattype.besluittypen.all()), [besluittype])

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_with_besluittype_another_catalogus_fail(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        besluittype = BesluitTypeFactory.create()
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluittypen": [f"http://testserver{reverse(besluittype)}"],
        }
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_patch_resultaattype_with_besluittypen(self, mock_shape, mock_fetch, m):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        besluittype = BesluitTypeFactory.create(catalogus=zaaktype.catalogus)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                archiefnominatie="blijvend_bewaren",
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url,
                {"besluittypen": [f"http://testserver{reverse(besluittype)}"]},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(resultaattype.besluittypen.all()), [besluittype])

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_patch_resultaattype_with_besluittype_another_catalogus_fail(
        self, mock_shape, mock_fetch, m
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        besluittype = BesluitTypeFactory.create()
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.get(resultaattypeomschrijving, json={"omschrijving": "init"})
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                resultaattypeomschrijving=resultaattypeomschrijving,
                archiefnominatie="blijvend_bewaren",
            )
            resultaattype_url = reverse(resultaattype)

            response = self.client.patch(
                resultaattype_url,
                {"besluittypen": [f"http://testserver{reverse(besluittype)}"]},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")


class ResultaatTypeFilterAPITests(APITestCase):
    maxDiff = None
    url = reverse_lazy("resultaattype-list")

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_on_zaaktype(self):
        zt1, zt2 = ZaakTypeFactory.create_batch(2, concept=False)
        rt1 = ResultaatTypeFactory.create(zaaktype=zt1)
        rt2 = ResultaatTypeFactory.create(zaaktype=zt2)

        rt1_uri = reverse(rt1)
        rt2_uri = reverse(rt2)

        zt1_uri = reverse("zaaktype-detail", kwargs={"uuid": zt1.uuid})
        zt2_uri = reverse("zaaktype-detail", kwargs={"uuid": zt2.uuid})
        zt1_url = "http://openzaak.nl{}".format(zt1_uri)
        list_url = reverse("resultaattype-list")

        response = self.client.get(
            list_url, {"zaaktype": zt1_url}, headers={"host": "openzaak.nl"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://openzaak.nl{rt1_uri}")
        self.assertEqual(response_data[0]["zaaktype"], f"http://openzaak.nl{zt1_uri}")
        self.assertNotEqual(response_data[0]["url"], f"http://openzaak.nl{rt2_uri}")
        self.assertNotEqual(
            response_data[0]["zaaktype"], f"http://openzaak.nl{zt2_uri}"
        )

    def test_filter_resultaattype_status_alles(self):
        ResultaatTypeFactory.create(zaaktype__concept=True)
        ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_resultaattype_status_concept(self):
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
        ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype1_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype1.uuid}
        )

        response = self.client.get(resultaattype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype1_url}")

    def test_filter_resultaattype_status_definitief(self):
        ResultaatTypeFactory.create(zaaktype__concept=True)
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype2_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype2.uuid}
        )

        response = self.client.get(resultaattype_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype2_url}")

    def test_validate_unknown_query_params(self):
        ResultaatTypeFactory.create_batch(2)
        url = reverse(ResultaatType)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_filter_zaaktype_identificatie(self):
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__identificatie="some", zaaktype__concept=False
        )
        ResultaatTypeFactory.create(
            zaaktype__identificatie="other", zaaktype__concept=False
        )

        response = self.client.get(self.url, {"zaaktypeIdentificatie": "some"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(resultaattype)}")

    def test_filter_geldigheid(self):
        resultaattype = ResultaatTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            zaaktype__concept=False,
        )
        ResultaatTypeFactory.create(
            datum_begin_geldigheid=date(2020, 2, 1), zaaktype__concept=False
        )

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(resultaattype)}")


class ResultaatTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        ResultaatTypeFactory.create_batch(2, zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ResultaatTypeFactory.create_batch(2, zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        ResultaatTypeFactory.create_batch(10, zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{resultaattype_list_url}?page=2&pageSize=5"
        )


@override_settings(SOLO_CACHE=None)
class ResultaatTypeValidationTests(SelectieLijstMixin, APITestCase):
    list_url = reverse_lazy(ResultaatType)

    def _setup_mock_responses(self, m):
        mock_selectielijst_oas_get(m)
        m.get(
            SELECTIELIJSTKLASSE_URL,
            json={
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "vast_te_leggen_datum",
            },
        )
        m.get(
            SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL,
            json={
                "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(
            SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL,
            json={
                "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
            },
        )
        m.get(RESULTAATTYPEOMSCHRIJVING_URL, json={"omschrijving": "test"})

    def _get_selectielijstklasse_url(self, afleidingswijze):
        if afleidingswijze == Afleidingswijze.afgehandeld:
            selectielijstklasse = SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL
        elif afleidingswijze == Afleidingswijze.termijn:
            selectielijstklasse = (
                SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL
            )
        else:
            selectielijstklasse = SELECTIELIJSTKLASSE_URL
        return selectielijstklasse

    @patch("openzaak.utils.validators.ResourceValidatorMixin._resolve_schema")
    @patch("openzaak.utils.validators.obj_has_shape", return_value=False)
    def test_validate_wrong_resultaattypeomschrijving(self, mock_shape, mock_fetch):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = (
            "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
        )
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": "https://garcia.org/",
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "resultaattypeomschrijving")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_selectielijstklasse_invalid_resource(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": "https://selectielijst.openzaak.nl/api/v1/resultaten/1234",
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get(
                "https://selectielijst.openzaak.nl/api/v1/resultaten/1234",
                json={"some": "incorrect property"},
            )

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "selectielijstklasse")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("openzaak.utils.validators.obj_has_shape", return_value=True)
    def test_selectielijstklasse_procestype_no_match_with_zaaktype_procestype(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": "http://somedifferentprocestypeurl.com/",
                    "procestermijn": Procestermijn.nihil,
                },
            )

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "procestype-mismatch")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("openzaak.utils.validators.obj_has_shape", return_value=True)
    def test_procestermijn_nihil_and_afleidingswijze_niet_afgehandeld_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.ander_datumkenmerk,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "identificatie",
                "objecttype": "pand",
                "registratie": "test",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.nihil,
                },
            )
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_procestermijn_empty_and_afleidingswijze_afgehandeld(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.ander_datumkenmerk,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "identificatie",
                "objecttype": "pand",
                "registratie": "test",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get("https://garcia.org/", json={"omschrijving": "bla"})
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": "",
                },
            )

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("openzaak.utils.validators.obj_has_shape", return_value=True)
    def test_procestermijn_ingeschatte_bestaansduur_procesobject_and_afleidingswijze_niet_termijn_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
                },
            )

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_procestermijn_empty_and_afleidingswijze_niet_termijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            mock_selectielijst_oas_get(m)
            m.get("https://garcia.org/", json={"omschrijving": "bla"})
            m.get(
                SELECTIELIJSTKLASSE_URL,
                json={
                    "url": SELECTIELIJSTKLASSE_URL,
                    "procesType": PROCESTYPE_URL,
                    "procestermijn": "",
                },
            )

            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_value_for_datumkenmerk(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["datumkenmerk"] = "identificatie"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)
                    response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.eigenschap,
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.datumkenmerk"
                    )
                    self.assertEqual(error["code"], "must-be-empty")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_datumkenmerk_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["datumkenmerk"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.eigenschap,
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.datumkenmerk"
                    )
                    self.assertEqual(error["code"], "required")
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_einddatum_bekend_true(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["einddatumBekend"] = True

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.afgehandeld,
                    Afleidingswijze.termijn,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.einddatumBekend"
                    )
                    self.assertEqual(error["code"], "must-be-empty")
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_einddatum_bekend_false(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["einddatumBekend"] = False

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_value_for_objecttype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["objecttype"] = "pand"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.objecttype"
                    )
                    self.assertEqual(error["code"], "must-be-empty")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_objecttype_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["objecttype"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.objecttype"
                    )
                    self.assertEqual(error["code"], "required")
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_value_for_registratie(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["registratie"] = "test"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.ander_datumkenmerk:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.registratie"
                    )
                    self.assertEqual(error["code"], "must-be-empty")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_registratie_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["registratie"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.ander_datumkenmerk:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.registratie"
                    )
                    self.assertEqual(error["code"], "required")
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_value_for_procestermijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["procestermijn"] = "P5M"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.termijn:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.procestermijn"
                    )
                    self.assertEqual(error["code"], "must-be-empty")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_procestermijn_null(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.values:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["procestermijn"] = None

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    self._setup_mock_responses(m)

                    response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.termijn:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.procestermijn"
                    )
                    self.assertEqual(error["code"], "required")
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
