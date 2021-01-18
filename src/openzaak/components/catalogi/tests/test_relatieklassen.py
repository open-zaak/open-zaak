# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings

from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..constants import RichtingChoices
from ..models import ZaakTypeInformatieObjectType
from .base import APITestCase
from .factories import (
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


class ZaakTypeInformatieObjectTypeAPITests(APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    list_url = reverse_lazy(ZaakTypeInformatieObjectType)

    def test_get_list_default_definitief(self):
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")

    def test_get_detail(self):
        ztiot = ZaakTypeInformatieObjectTypeFactory.create()
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
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziot = ZaakTypeInformatieObjectType.objects.get(volgnummer=13)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_create_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_ziot_fail_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_create_ziot_fail_not_unique(self):
        ziot = ZaakTypeInformatieObjectTypeFactory(volgnummer=1)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=ziot.zaaktype.catalogus
        )
        data = {
            "zaaktype": f"http://testserver.com{reverse(ziot.zaaktype)}",
            "informatieobjecttype": f"http://testserver.com{reverse(informatieobjecttype)}",
            "volgnummer": ziot.volgnummer,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_delete_ziot(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create()
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_not_concept_zaaktype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(zaaktype__concept=False)
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_not_concept_informatieobjecttype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_fail_not_concept(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_update_ziot(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_partial_update_ziot(self):
        zaaktype = ZaakTypeFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_update_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_update_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_update_ziot_not_concept_zaaktype_and_informatieobjecttype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_partial_update_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_partial_update_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_partial_update_ziot_not_concept_zaaktype_and_informatieobjecttype_fails(
        self,
    ):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")


class ZaakTypeInformatieObjectTypeFilterAPITests(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakTypeInformatieObjectType)

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_zaaktype(self):
        ztiot1, ztiot2 = ZaakTypeInformatieObjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://openzaak.nl{reverse(ztiot1)}"
        zaaktype1_uri = reverse(ztiot1.zaaktype)
        zaaktype2_uri = reverse(ztiot2.zaaktype)
        zaaktype1_url = f"http://openzaak.nl{zaaktype1_uri}"

        response = self.client.get(
            self.list_url, {"zaaktype": zaaktype1_url}, HTTP_HOST="openzaak.nl"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(data[0]["zaaktype"], f"http://openzaak.nl{zaaktype1_uri}")
        self.assertNotEqual(data[0]["zaaktype"], f"http://openzaak.nl{zaaktype2_uri}")

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_informatieobjecttype(self):
        ztiot1, ztiot2 = ZaakTypeInformatieObjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://openzaak.nl{reverse(ztiot1)}"
        informatieobjecttype1_uri = reverse(ztiot1.informatieobjecttype)
        informatieobjecttype2_uri = reverse(ztiot2.informatieobjecttype)
        informatieobjecttype1_url = f"http://openzaak.nl{informatieobjecttype1_uri}"

        response = self.client.get(
            self.list_url,
            {"informatieobjecttype": informatieobjecttype1_url},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(
            data[0]["informatieobjecttype"],
            f"http://openzaak.nl{informatieobjecttype1_uri}",
        )
        self.assertNotEqual(
            data[0]["informatieobjecttype"],
            f"http://openzaak.nl{informatieobjecttype2_uri}",
        )

    def test_filter_ziot_status_alles(self):
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 4)

    def test_filter_ziot_status_concept(self):
        ziot1 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot1_url = reverse(ziot1)
        ziot2_url = reverse(ziot2)
        ziot3_url = reverse(ziot3)

        response = self.client.get(self.list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 3)

        urls = {obj["url"] for obj in data}
        self.assertEqual(
            urls,
            {
                f"http://testserver{ziot1_url}",
                f"http://testserver{ziot2_url}",
                f"http://testserver{ziot3_url}",
            },
        )

    def test_filter_ziot_status_definitief(self):
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")

    def test_validate_unknown_query_params(self):
        ZaakTypeInformatieObjectTypeFactory.create_batch(2)
        url = reverse(ZaakTypeInformatieObjectType)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class ZaakTypeInformatieObjectTypePaginationTestCase(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakTypeInformatieObjectType)

    def test_pagination_default(self):
        ZaakTypeInformatieObjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakTypeInformatieObjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])


class ZaakTypeInformatieObjectTypeValidationTests(APITestCase):
    maxDiff = None

    list_url = reverse_lazy(ZaakTypeInformatieObjectType)

    def test_catalogus_mismatch(self):
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")
