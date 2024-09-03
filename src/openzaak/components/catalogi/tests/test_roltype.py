# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import override_settings

from rest_framework import status
from vng_api_common.constants import ComponentTypes, RolOmschrijving
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..models import RolType
from .base import APITestCase
from .factories import RolTypeFactory, ZaakTypeFactory


class RolTypeAPITests(APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    def test_get_list_default_definitief(self):
        RolTypeFactory.create(zaaktype__concept=True)
        roltype2 = RolTypeFactory.create(zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")
        roltype2_url = reverse("roltype-detail", kwargs={"uuid": roltype2.uuid})

        response = self.client.get(roltype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{roltype2_url}")

    def test_get_detail(self):
        rol_type = RolTypeFactory.create(
            omschrijving="Vergunningaanvrager",
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype__catalogus=self.catalogus,
            datum_begin_geldigheid=date(2023, 1, 1),
            datum_einde_geldigheid=date(2023, 12, 1),
        )
        zaaktype = rol_type.zaaktype
        rol_type_detail_url = reverse("roltype-detail", kwargs={"uuid": rol_type.uuid})
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        response = self.client.get(rol_type_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            "url": f"http://testserver{rol_type_detail_url}",
            "zaaktype": f"http://testserver{zaaktype_url}",
            "zaaktypeIdentificatie": rol_type.zaaktype.identificatie,
            "omschrijving": "Vergunningaanvrager",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
            "catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
            "beginObject": "2023-01-01",
            "eindeObject": "2023-12-01",
        }
        self.assertEqual(expected, response.json())

    def test_create_roltype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        rol_type_list_url = reverse("roltype-list")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "Vergunningaanvrager",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
        }

        response = self.client.post(rol_type_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        roltype = RolType.objects.get()
        self.assertEqual(roltype.omschrijving, "Vergunningaanvrager")
        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(roltype.datum_begin_geldigheid, date(2023, 1, 1))
        self.assertEqual(roltype.datum_einde_geldigheid, date(2023, 12, 1))

    def test_create_roltype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        rol_type_list_url = reverse("roltype-list")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "Vergunningaanvrager",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.post(rol_type_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_create_roltype_with_end_date_before_start_date(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        rol_type_list_url = reverse("roltype-list")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "Vergunningaanvrager",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
            "beginGeldigheid": "2023-12-01",
            "eindeGeldigheid": "2023-01-01",
        }

        response = self.client.post(rol_type_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "date-mismatch")

    def test_delete_roltype(self):
        roltype = RolTypeFactory.create()
        roltype_url = reverse("roltype-detail", kwargs={"uuid": roltype.uuid})

        response = self.client.delete(roltype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RolType.objects.filter(id=roltype.id))

    def test_delete_roltype_fail_not_concept_zaaktype(self):
        roltype = RolTypeFactory.create(zaaktype__concept=False)
        roltype_url = reverse("roltype-detail", kwargs={"uuid": roltype.uuid})

        response = self.client.delete(roltype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_update_roltype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.put(roltype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

        roltype.refresh_from_db()
        self.assertEqual(roltype.omschrijving, "aangepast")

    def test_update_roltype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.put(roltype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_update_roltype_add_relation_to_non_concept_zaaktype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        roltype = RolTypeFactory.create()
        roltype_url = reverse(roltype)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.put(roltype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_partial_update_roltype(self):
        zaaktype = ZaakTypeFactory.create()
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)

        response = self.client.patch(roltype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

        roltype.refresh_from_db()
        self.assertEqual(roltype.omschrijving, "aangepast")

    def test_partial_update_roltype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)

        response = self.client.patch(roltype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_partial_update_roltype_add_relation_to_non_concept_zaaktype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        roltype = RolTypeFactory.create()
        roltype_url = reverse(roltype)

        response = self.client.patch(roltype_url, {"zaaktype": zaaktype_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)


class FilterValidationTests(APITestCase):
    def test_invalid_filters(self):
        url = reverse("roltype-list")

        invalid_filters = {
            "omschrijvingGeneriek": "invalid-option",  # bestaat niet
            "foo": "bar",  # unsupported param
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RolTypeFilterAPITests(APITestCase):
    maxDiff = None
    url = reverse_lazy("roltype-list")

    def test_filter_roltype_status_alles(self):
        RolTypeFactory.create(zaaktype__concept=True)
        RolTypeFactory.create(zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")

        response = self.client.get(roltype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_roltype_status_concept(self):
        roltype1 = RolTypeFactory.create(zaaktype__concept=True)
        RolTypeFactory.create(zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")
        roltype1_url = reverse("roltype-detail", kwargs={"uuid": roltype1.uuid})

        response = self.client.get(roltype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{roltype1_url}")

    def test_filter_roltype_status_definitief(self):
        RolTypeFactory.create(zaaktype__concept=True)
        roltype2 = RolTypeFactory.create(zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")
        roltype2_url = reverse("roltype-detail", kwargs={"uuid": roltype2.uuid})

        response = self.client.get(roltype_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{roltype2_url}")

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_zaaktype(self):
        roltype1 = RolTypeFactory.create(zaaktype__concept=False)
        RolTypeFactory.create(zaaktype__concept=False)
        zaaktype1 = roltype1.zaaktype
        roltype_list_url = reverse("roltype-list")
        roltype1_url = reverse(roltype1)
        zaaktype1_url = reverse(zaaktype1)

        response = self.client.get(
            roltype_list_url,
            {"zaaktype": f"http://openzaak.nl{zaaktype1_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://openzaak.nl{roltype1_url}")

    def test_filter_zaaktype_identificatie(self):
        roltype = RolTypeFactory.create(
            zaaktype__identificatie="some", zaaktype__concept=False
        )
        RolTypeFactory.create(zaaktype__identificatie="other", zaaktype__concept=False)

        response = self.client.get(self.url, {"zaaktypeIdentificatie": "some"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(roltype)}")

    def test_filter_geldigheid(self):
        roltype = RolTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            zaaktype__concept=False,
        )
        RolTypeFactory.create(
            datum_begin_geldigheid=date(2020, 2, 1), zaaktype__concept=False
        )

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(roltype)}")


class RolTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        RolTypeFactory.create_batch(2, zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")

        response = self.client.get(roltype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        RolTypeFactory.create_batch(2, zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")

        response = self.client.get(roltype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        RolTypeFactory.create_batch(10, zaaktype__concept=False)
        roltype_list_url = reverse("roltype-list")

        response = self.client.get(roltype_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{roltype_list_url}?page=2&pageSize=5"
        )
