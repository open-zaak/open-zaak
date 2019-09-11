from rest_framework import status
from vng_api_common.tests import TypeCheckMixin, reverse

from ..constants import FormaatChoices
from ..models import Eigenschap
from .base import APITestCase
from .factories import EigenschapFactory, EigenschapSpecificatieFactory, ZaakTypeFactory
from .utils import get_operation_url


class EigenschapAPITests(TypeCheckMixin, APITestCase):
    maxDiff = None

    def test_list_eigenschappen(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        eigenschap1 = EigenschapFactory.create(
            eigenschapnaam="objecttype",
            zaaktype=zaaktype,
            specificatie_van_eigenschap=EigenschapSpecificatieFactory.create(
                formaat=FormaatChoices.tekst,
                lengte=255,
                kardinaliteit="1",
                waardenverzameling=["boot", "zwerfvuil"],
            ),
        )
        EigenschapFactory.create(
            eigenschapnaam="boot.naam",
            zaaktype=zaaktype,
            specificatie_van_eigenschap=EigenschapSpecificatieFactory.create(
                groep="boot",
                formaat=FormaatChoices.tekst,
                lengte=255,
                kardinaliteit="1",
            ),
        )
        EigenschapFactory.create(
            eigenschapnaam="boot.rederij",
            zaaktype=zaaktype,
            specificatie_van_eigenschap=EigenschapSpecificatieFactory.create(
                groep="boot",
                formaat=FormaatChoices.tekst,
                lengte=255,
                kardinaliteit="1",
            ),
        )

        url = get_operation_url(
            "eigenschap_list",
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]

        self.assertEqual(len(response_data), 3)
        self.assertResponseTypes(
            response_data[0],
            {
                ("url", str),
                ("naam", str),
                ("definitie", str),
                ("specificatie", dict),
                ("toelichting", str),
                ("zaaktype", str),
            },
        )

        eigenschap_objecttype = next(
            (eig for eig in response_data if eig["naam"] == "objecttype")
        )

        zaaktype_url = get_operation_url(
            "zaaktype_read", catalogus_uuid=zaaktype.catalogus.uuid, uuid=zaaktype.uuid
        )
        detail_url = get_operation_url(
            "eigenschap_read",
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
            uuid=eigenschap1.uuid,
        )
        self.assertEqual(
            eigenschap_objecttype,
            {
                "url": f"http://testserver{detail_url}",
                "naam": "objecttype",
                "definitie": "",
                "zaaktype": f"http://testserver{zaaktype_url}",
                "toelichting": "",
                "specificatie": {
                    "formaat": FormaatChoices.tekst,
                    "groep": "",
                    "kardinaliteit": "1",
                    "lengte": "255",
                    "waardenverzameling": ["boot", "zwerfvuil"],
                },
            },
        )

    def test_get_list_default_definitief(self):
        eigenschap1 = EigenschapFactory.create(zaaktype__concept=True)
        eigenschap2 = EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")
        eigenschap2_url = reverse(
            "eigenschap-detail", kwargs={"uuid": eigenschap2.uuid}
        )

        response = self.client.get(eigenschap_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{eigenschap2_url}")

    def test_get_detail(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        specificatie = EigenschapSpecificatieFactory.create(
            kardinaliteit="1", lengte="1", groep="groep"
        )
        eigenschap = EigenschapFactory.create(
            eigenschapnaam="Beoogd product",
            zaaktype=zaaktype,
            specificatie_van_eigenschap=specificatie,
        )
        eigenschap_detail_url = reverse(
            "eigenschap-detail", kwargs={"uuid": eigenschap.uuid}
        )

        response = self.client.get(eigenschap_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            "url": "http://testserver{}".format(eigenschap_detail_url),
            "naam": "Beoogd product",
            "definitie": "",
            "specificatie": {
                "formaat": "",
                "groep": "groep",
                "kardinaliteit": "1",
                "lengte": "1",
                "waardenverzameling": [],
            },
            "toelichting": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
        }
        self.assertEqual(expected, response.json())

    def test_create_eigenschap(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        eigenschap_list_url = reverse("eigenschap-list")
        data = {
            "naam": "Beoogd product",
            "definitie": "test",
            "toelichting": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
        }

        response = self.client.post(eigenschap_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        eigenschap = Eigenschap.objects.get()

        self.assertEqual(eigenschap.eigenschapnaam, "Beoogd product")
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_create_eigenschap_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        eigenschap_list_url = reverse("eigenschap-list")
        data = {
            "naam": "Beoogd product",
            "definitie": "test",
            "toelichting": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
        }

        response = self.client.post(eigenschap_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"],
            "Creating a related object to non-concept object is forbidden",
        )

    def test_delete_eigenschap(self):
        eigenschap = EigenschapFactory.create()
        eigenschap_url = reverse("eigenschap-detail", kwargs={"uuid": eigenschap.uuid})

        response = self.client.delete(eigenschap_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Eigenschap.objects.filter(id=eigenschap.id))

    def test_delete_eigenschap_fail_not_concept_zaaktype(self):
        eigenschap = EigenschapFactory.create(zaaktype__concept=False)
        informatieobjecttypee_url = reverse(
            "eigenschap-detail", kwargs={"uuid": eigenschap.uuid}
        )

        response = self.client.delete(informatieobjecttypee_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["detail"], "Alleen concepten kunnen worden verwijderd.")


class EigenschapFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_eigenschap_status_alles(self):
        EigenschapFactory.create(zaaktype__concept=True)
        EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")

        response = self.client.get(eigenschap_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_eigenschap_status_concept(self):
        eigenschap1 = EigenschapFactory.create(zaaktype__concept=True)
        eigenschap2 = EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")
        eigenschap1_url = reverse(
            "eigenschap-detail", kwargs={"uuid": eigenschap1.uuid}
        )

        response = self.client.get(eigenschap_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{eigenschap1_url}")

    def test_filter_eigenschap_status_definitief(self):
        eigenschap1 = EigenschapFactory.create(zaaktype__concept=True)
        eigenschap2 = EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")
        eigenschap2_url = reverse(
            "eigenschap-detail", kwargs={"uuid": eigenschap2.uuid}
        )

        response = self.client.get(eigenschap_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{eigenschap2_url}")


class EigenschapPaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        EigenschapFactory.create_batch(2, zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")

        response = self.client.get(eigenschap_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        EigenschapFactory.create_batch(2, zaaktype__concept=False)
        eigenschap_list_url = reverse("eigenschap-list")

        response = self.client.get(eigenschap_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
