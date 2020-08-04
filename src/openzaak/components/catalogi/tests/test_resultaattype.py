# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from copy import deepcopy
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
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.utils.tests import mock_client

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..models import ResultaatType
from .base import APITestCase
from .contants import BrondatumArchiefprocedureExampleMapping as MAPPING
from .factories import ResultaatTypeFactory, ZaakTypeFactory

PROCESTYPE_URL = "http://referentielijsten.nl/procestypen/1234"
SELECTIELIJSTKLASSE_URL = "http://example.com/resultaten/1234"
SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL = "http://example.com/resultaten/4321"
SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL = (
    "http://example.com/resultaten/5678"
)
RESULTAATTYPEOMSCHRIJVING_URL = "http://example.com/omschrijving/1"


class ResultaatTypeAPITests(TypeCheckMixin, APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    list_url = reverse_lazy(ResultaatType)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Service.objects.create(
            api_root="http://example.com/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            label="Selectielijst",
        )

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
            m.register_uri(
                "GET", resultaattypeomschrijving, json={"omschrijving": "init"}
            )
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

        afleidingswijze = resultaattype.brondatum_archiefprocedure_afleidingswijze
        procestermijn = resultaattype.brondatum_archiefprocedure_procestermijn

        self.assertEqual(brondatumArchiefprocedure["afleidingswijze"], afleidingswijze)

        # Verify that the procestermijn was serialized correctly
        self.assertEqual(brondatumArchiefprocedure["procestermijn"], procestermijn)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype(self, mock_shape, mock_fetch):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = ResultaatType.objects.get()

        self.assertEqual(resultaattype.omschrijving_generiek, "test")
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure_afleidingswijze,
            Afleidingswijze.afgehandeld,
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype_brondatum_archiefprocedure_null(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": None,
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
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
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype_brondatum_archiefprocedure_null_with_vernietigen(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "vernietigen",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": None,
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_resultaattype_brondatum_archiefprocedure(self):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL,)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.register_uri(
                "GET", resultaattypeomschrijving, json={"omschrijving": "init"}
            )
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
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype_fail_not_concept_zaaktype(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

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
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_derive_archiefactiedatum_from_selectielijstklasse(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                m.register_uri(
                    "GET", SELECTIELIJSTKLASSE_URL, json={"bewaartermijn": "P5Y"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["archiefactietermijn"], "P5Y")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_fail_not_concept_zaaktype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
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
            m.register_uri(
                "GET", resultaattypeomschrijving, json={"omschrijving": "init"}
            )
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
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_partial_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(archiefnominatie="vernietigen")
        resultaattype_url = reverse(resultaattype)

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            response = self.client.patch(resultaattype_url, {"zaaktype": zaaktype_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_omschrijving_generiek(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse(zaaktype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET", resultaattypeomschrijving_url, json={"omschrijving": "init"}
            )
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
            m.register_uri(
                "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
            )
            response = self.client.patch(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving_generiek"], "test")


class ResultaatTypeFilterAPITests(APITestCase):
    maxDiff = None

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
            list_url, {"zaaktype": zt1_url}, HTTP_HOST="openzaak.nl"
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


class ResultaatTypeValidationTests(APITestCase):
    list_url = reverse_lazy(ResultaatType)
    RESPONSES = {
        SELECTIELIJSTKLASSE_URL: {
            "url": SELECTIELIJSTKLASSE_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": "vast_te_leggen_datum",
        },
        SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL: {
            "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": Procestermijn.nihil,
        },
        SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL: {
            "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
        },
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Service.objects.create(
            api_root="http://example.com/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            label="Selectielijst",
        )

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

    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=False)
    def test_validate_wrong_resultaattypeomschrijving(self, mock_shape, mock_fetch):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
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
            m.register_uri(
                "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
            )
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "resultaattypeomschrijving")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_selectielijstklasse_invalid_resource(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            "http://example.com/resultaten/1234": {"some": "incorrect property"}
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": "http://example.com/resultaten/1234",
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

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "selectielijstklasse")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_selectielijstklasse_procestype_no_match_with_zaaktype_procestype(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": "http://somedifferentprocestypeurl.com/",
                "procestermijn": Procestermijn.nihil,
            }
        }

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

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "procestype-mismatch")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_nihil_and_afleidingswijze_niet_afgehandeld_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

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

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_empty_and_afleidingswijze_afgehandeld(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "",
            }
        }

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

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", "https://garcia.org/", json={"omschrijving": "bla"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_ingeschatte_bestaansduur_procesobject_and_afleidingswijze_niet_termijn_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
            }
        }

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

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_empty_and_afleidingswijze_niet_termijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "",
            }
        }

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

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", "https://garcia.org/", json={"omschrijving": "bla"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_datumkenmerk(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_datumkenmerk_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_einddatum_bekend_true(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_einddatum_bekend_false(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_objecttype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_objecttype_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_registratie(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_registratie_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_procestermijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_null(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
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
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
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
