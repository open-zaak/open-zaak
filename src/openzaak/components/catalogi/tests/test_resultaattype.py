from unittest.mock import patch

from django.test import override_settings

import requests_mock
from rest_framework import status
from vng_api_common.constants import BrondatumArchiefprocedureAfleidingswijze
from vng_api_common.tests import (
    TypeCheckMixin,
    get_validation_errors,
    reverse,
    reverse_lazy,
)
from zds_client.tests.mocks import mock_client

from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..models import ResultaatType
from .base import APITestCase
from .factories import ResultaatTypeFactory, ZaakTypeFactory

PROCESTYPE_URL = "http://referentielijsten.nl/procestypen/1234"
SELECTIELIJSTKLASSE_URL = "http://example.com/resultaten/1234"


class ResultaatTypeAPITests(TypeCheckMixin, APITestCase):
    maxDiff = None

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
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
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
        resultaattype = ResultaatTypeFactory.create()
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
                    "afleidingswijze": None,
                    "datumkenmerk": None,
                    "einddatumBekend": False,
                    "objecttype": None,
                    "registratie": None,
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
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
            BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"],
            "Creating a related object to non-concept object is forbidden",
        )

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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["detail"], "Alleen concepten kunnen worden verwijderd.")


class ResultaatTypeFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_on_zaaktype(self):
        zt1, zt2 = ZaakTypeFactory.create_batch(2, concept=False)
        rt1 = ResultaatTypeFactory.create(zaaktype=zt1)
        rt1_url = f"http://testserver{reverse(rt1)}"
        rt2 = ResultaatTypeFactory.create(zaaktype=zt2)
        rt2_url = f"http://testserver{reverse(rt2)}"
        zt1_url = "http://testserver{}".format(
            reverse("zaaktype-detail", kwargs={"uuid": zt1.uuid})
        )
        zt2_url = "http://testserver{}".format(
            reverse("zaaktype-detail", kwargs={"uuid": zt2.uuid})
        )
        list_url = reverse("resultaattype-list")

        response = self.client.get(list_url, {"zaaktype": zt1_url})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], rt1_url)
        self.assertEqual(response_data[0]["zaaktype"], zt1_url)
        self.assertNotEqual(response_data[0]["url"], rt2_url)
        self.assertNotEqual(response_data[0]["zaaktype"], zt2_url)

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
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
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
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
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

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

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
                "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
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

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")
