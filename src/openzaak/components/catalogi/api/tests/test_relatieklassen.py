from unittest import skip

from rest_framework import status
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.models import ZaakInformatieobjectType
from openzaak.components.catalogi.models.choices import RichtingChoices
from openzaak.components.catalogi.models.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakInformatieobjectTypeArchiefregimeFactory,
    ZaakInformatieobjectTypeFactory,
    ZaakTypeFactory,
)

from .base import APITestCase


class ZaakInformatieobjectTypeAPITests(APITestCase):
    maxDiff = None

    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_get_list_default_definitief(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")

    def test_get_detail(self):
        ztiot = ZaakInformatieobjectTypeFactory.create()
        url = reverse(ztiot)
        zaaktype_url = reverse(ztiot.zaaktype)
        informatieobjecttype_url = reverse(ztiot.informatieobjecttype)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "url": f"http://testserver{url}",
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": ztiot.volgnummer,
            "richting": ztiot.richting,
            "statustype": None,
        }
        self.assertEqual(response.json(), expected)

    def test_create_ziot(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziot = ZaakInformatieobjectType.objects.get(volgnummer=13)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_create_ziot_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"],
            "Creating relations between non-concept objects is forbidden",
        )

    def test_create_ziot_fail_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"],
            "Creating relations between non-concept objects is forbidden",
        )

    def test_delete_ziot(self):
        ziot = ZaakInformatieobjectTypeFactory.create()
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakInformatieobjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_fail_not_concept_zaaktype(self):
        ziot = ZaakInformatieobjectTypeFactory.create(zaaktype__concept=False)
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["detail"], "Alleen concepten kunnen worden verwijderd.")

    def test_delete_ziot_fail_not_concept_informatieobjecttype(self):
        ziot = ZaakInformatieobjectTypeFactory.create(
            informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["detail"], "Alleen concepten kunnen worden verwijderd.")


class ZaakInformatieobjectTypeFilterAPITests(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_filter_zaaktype(self):
        ztiot1, ztiot2 = ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://testserver{reverse(ztiot1)}"
        zaaktype1_url = reverse(ztiot1.zaaktype)
        zaaktype2_url = reverse(ztiot2.zaaktype)
        zaaktype1_url = f"http://testserver{zaaktype1_url}"
        zaaktype2_url = f"http://testserver{zaaktype2_url}"

        response = self.client.get(self.list_url, {"zaaktype": zaaktype1_url})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(data[0]["zaaktype"], zaaktype1_url)
        self.assertNotEqual(data[0]["zaaktype"], zaaktype2_url)

    def test_filter_informatieobjecttype(self):
        ztiot1, ztiot2 = ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://testserver{reverse(ztiot1)}"
        informatieobjecttype1_url = reverse(ztiot1.informatieobjecttype)
        informatieobjecttype2_url = reverse(ztiot2.informatieobjecttype)
        informatieobjecttype1_url = f"http://testserver{informatieobjecttype1_url}"
        informatieobjecttype2_url = f"http://testserver{informatieobjecttype2_url}"

        response = self.client.get(
            self.list_url, {"informatieobjecttype": informatieobjecttype1_url}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(data[0]["informatieobjecttype"], informatieobjecttype1_url)
        self.assertNotEqual(data[0]["informatieobjecttype"], informatieobjecttype2_url)

    def test_filter_ziot_status_alles(self):
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 4)

    def test_filter_ziot_status_concept(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot1_url = reverse(ziot1)

        response = self.client.get(self.list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot1_url}")

    def test_filter_ziot_status_definitief(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")


class ZaakInformatieobjectTypePaginationTestCase(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_pagination_default(self):
        ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])


@skip("Not MVP yet")
class ZaakInformatieobjectTypeArchiefregimeAPITests(APITestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype__catalogus=self.catalogus,
            informatieobjecttype__catalogus=self.catalogus,
            informatieobjecttype__zaaktypes=None,
            volgnummer=1,
        )

        self.informatieobjecttype = self.ziot.informatieobjecttype
        self.zaaktype = self.ziot.zaaktype

        self.rstiotarc = ZaakInformatieobjectTypeArchiefregimeFactory.create(
            zaak_informatieobject_type=self.ziot,
            resultaattype__is_relevant_voor=self.zaaktype,
            resultaattype__bepaalt_afwijkend_archiefregime_van=None,
        )

        self.resultaattype = self.rstiotarc.resultaattype

        self.rstiotarc_list_url = reverse(
            "api:rstiotarc-list",
            kwargs={
                "version": self.API_VERSION,
                "catalogus_pk": self.catalogus.pk,
                "zaaktype_pk": self.zaaktype.pk,
            },
        )

        self.rstiotarc_detail_url = reverse(
            "api:rstiotarc-detail",
            kwargs={
                "version": self.API_VERSION,
                "catalogus_pk": self.catalogus.pk,
                "zaaktype_pk": self.zaaktype.pk,
                "pk": self.rstiotarc.pk,
            },
        )

    def test_get_list(self):
        response = self.api_client.get(self.rstiotarc_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)

    def test_get_detail(self):
        response = self.api_client.get(self.rstiotarc_detail_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "url": "http://testserver{}".format(self.rstiotarc_detail_url),
            "gerelateerde": "http://testserver{}".format(
                reverse(
                    "api:informatieobjecttype-detail",
                    args=[
                        self.API_VERSION,
                        self.catalogus.pk,
                        self.informatieobjecttype.pk,
                    ],
                )
            ),
            "rstzdt.archiefactietermijn": 7,
            "rstzdt.archiefnominatie": "",
            "rstzdt.selectielijstklasse": None,
        }
        self.assertEqual(response.json(), expected)
