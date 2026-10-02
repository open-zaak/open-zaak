# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import uuid

from django.test import TestCase, override_settings, tag
from django.utils.translation import gettext_lazy as _

import requests
import requests_mock
from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.documenten.tests.utils import (
    get_informatieobjecttype_response,
)
from openzaak.tests.utils import mock_drc_oas_get
from openzaak.utils.urls import reverse, reverse_lazy

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..constants import RichtingChoices
from ..models import (
    BesluitType,
    BesluitTypeInformatieObjectType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from ..validators import validate_zaaktype_for_publish
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)

BASE = "https://external.documenten.nl/api/v1/"
RESOURCES_PUBLISHED_ERROR = _("All related resources should be published")
CATALOGUS = f"{BASE}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"


def new_external_iotype() -> str:
    return f"{BASE}informatieobjecttypen/{uuid.uuid4()}"


class ExternalInformatieObjectTypeMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # type: ignore

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=BASE,
            label="external documenten",
            auth_type=AuthTypes.no_auth,
        )

    def mock_external_iotype(
        self, m: requests_mock.Mocker, url: str, concept: bool = False
    ) -> None:
        mock_drc_oas_get(m)
        m.get(
            url,
            json={
                **get_informatieobjecttype_response(CATALOGUS, url),
                "concept": concept,
            },
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakTypeInformatieObjectTypeExternalTests(
    ExternalInformatieObjectTypeMixin, APITestCase
):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    list_url = reverse_lazy(ZaakTypeInformatieObjectType)

    def _data(self, zaaktype, informatieobjecttype: str) -> dict:
        return {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "informatieobjecttype": informatieobjecttype,
            "volgnummer": 1,
            "richting": RichtingChoices.inkomend,
        }

    def test_create_with_external_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        iotype = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, iotype)
            response = self.client.post(self.list_url, self._data(zaaktype, iotype))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.json()["informatieobjecttype"], iotype)

        relation = ZaakTypeInformatieObjectType.objects.get()
        self.assertIsNone(relation._informatieobjecttype)
        self.assertEqual(relation._iotype_url, iotype)

    def test_retrieve_with_external_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        iotype = new_external_iotype()
        relation = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=iotype,
            volgnummer=1,
            richting=RichtingChoices.inkomend,
        )

        with requests_mock.Mocker():
            response = self.client.get(reverse(relation))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["informatieobjecttype"], iotype)

    def test_filter_on_external_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        iotype = new_external_iotype()
        relation = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=iotype,
            volgnummer=1,
            richting=RichtingChoices.inkomend,
        )
        ZaakTypeInformatieObjectTypeFactory.create(zaaktype=zaaktype, volgnummer=2)

        response = self.client.get(
            self.list_url, {"informatieobjecttype": iotype, "status": "alles"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], f"http://testserver{reverse(relation)}")

    def test_create_with_external_informatieobjecttype_non_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        iotype = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, iotype)
            response = self.client.post(self.list_url, self._data(zaaktype, iotype))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def _create_relation(self, zaaktype) -> ZaakTypeInformatieObjectType:
        return ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=new_external_iotype(),
            volgnummer=1,
            richting=RichtingChoices.inkomend,
        )

    def _mock_relation_iotype(
        self, m, relation, concept: bool | None, unavailable: bool
    ) -> None:
        if unavailable:
            m.get(
                relation._iotype_url,
                exc=requests.exceptions.ConnectTimeout("timed out"),
            )
        elif concept is not None:
            self.mock_external_iotype(m, relation._iotype_url, concept=concept)

    def _patch(self, relation, concept: bool | None = None, unavailable=False):
        with requests_mock.Mocker() as m:
            self._mock_relation_iotype(m, relation, concept, unavailable)
            return self.client.patch(
                reverse(relation), {"richting": RichtingChoices.uitgaand}
            )

    def _delete(self, relation, concept: bool | None = None, unavailable=False):
        with requests_mock.Mocker() as m:
            self._mock_relation_iotype(m, relation, concept, unavailable)
            return self.client.delete(reverse(relation))

    def test_update_concept_zaaktype_does_not_fetch_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=True)
        )

        response = self._patch(relation)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        relation.refresh_from_db()
        self.assertEqual(relation.richting, RichtingChoices.uitgaand)

    def test_update_published_zaaktype_published_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._patch(relation, concept=False)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_update_published_zaaktype_concept_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._patch(relation, concept=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_published_zaaktype_informatieobjecttype_unavailable(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._patch(relation, unavailable=True)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "external-informatieobjecttype-unavailable")

    def test_delete_concept_zaaktype_does_not_fetch_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=True)
        )

        response = self._delete(relation)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_delete_published_zaaktype_published_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._delete(relation, concept=False)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ZaakTypeInformatieObjectType.objects.exists())

    def test_delete_published_zaaktype_concept_informatieobjecttype(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._delete(relation, concept=True)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_delete_published_zaaktype_informatieobjecttype_unavailable(self):
        relation = self._create_relation(
            ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        )

        response = self._delete(relation, unavailable=True)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ZaakTypeInformatieObjectType.objects.exists())

    def test_create_published_zaaktype_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        iotype = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, iotype, concept=True)
            response = self.client.post(self.list_url, self._data(zaaktype, iotype))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_with_external_informatieobjecttype_unknown_service(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        iotype = (
            f"https://unknown.documenten.nl/api/v1/informatieobjecttypen/{uuid.uuid4()}"
        )

        response = self.client.post(self.list_url, self._data(zaaktype, iotype))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "unknown-service")
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_create_with_external_informatieobjecttype_not_json(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        iotype = new_external_iotype()

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(iotype, text="not json")
            response = self.client.post(self.list_url, self._data(zaaktype, iotype))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_with_local_informatieobjecttype_still_works(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus, zaaktypen=[]
        )
        url = f"http://testserver{reverse(iotype, namespace='documenten')}"

        response = self.client.post(self.list_url, self._data(zaaktype, url))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            ZaakTypeInformatieObjectType.objects.get().informatieobjecttype, iotype
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitTypeExternalInformatieObjectTypenTests(
    ExternalInformatieObjectTypeMixin, APITestCase
):
    list_url = reverse_lazy(BesluitType, namespace="zaken")

    def _data(self, informatieobjecttypen: list[str]) -> dict:
        return {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "omschrijvingGeneriek": "",
            "besluitcategorie": "",
            "reactietermijn": "P14D",
            "publicatieIndicatie": True,
            "publicatietekst": "",
            "publicatietermijn": None,
            "toelichting": "",
            "informatieobjecttypen": informatieobjecttypen,
            "beginGeldigheid": "2019-01-01",
        }

    def test_create_with_external_informatieobjecttypen(self):
        local = InformatieObjectTypeFactory.create(catalogus=self.catalogus)
        local_url = f"http://testserver{reverse(local, namespace='documenten')}"
        external = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, external)
            response = self.client.post(
                self.list_url, self._data([local_url, external])
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["informatieobjecttypen"], [local_url, external]
        )

        besluittype = BesluitType.objects.get()
        self.assertEqual(list(besluittype.informatieobjecttypen.all()), [local])
        relations = BesluitTypeInformatieObjectType.objects.order_by("pk")
        self.assertEqual(relations.count(), 2)
        self.assertEqual(relations[0].informatieobjecttype, local)
        self.assertEqual(relations[1]._iotype_url, external)

    def test_retrieve_with_external_informatieobjecttypen(self):
        besluittype = BesluitTypeFactory.create(
            catalogus=self.catalogus, informatieobjecttypen=[]
        )
        local = InformatieObjectTypeFactory.create(catalogus=self.catalogus)
        external = new_external_iotype()
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=local
        )
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=external
        )

        with requests_mock.Mocker():
            response = self.client.get(reverse(besluittype, namespace="zaken"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["informatieobjecttypen"],
            [f"http://testserver{reverse(local, namespace='documenten')}", external],
        )
        self.assertEqual(response.json()["vastgelegdIn"], [local.omschrijving])

    def test_update_replaces_external_informatieobjecttypen(self):
        besluittype = BesluitTypeFactory.create(
            catalogus=self.catalogus, informatieobjecttypen=[]
        )
        old = new_external_iotype()
        new = new_external_iotype()
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=old
        )

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, new)
            response = self.client.put(
                reverse(besluittype, namespace="zaken"), self._data([new])
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [
                r._iotype_url
                for r in besluittype.besluittypeinformatieobjecttype_set.all()
            ],
            [new],
        )

    def test_create_with_same_external_informatieobjecttype_twice(self):
        external = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, external)
            response = self.client.post(self.list_url, self._data([external, external]))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(BesluitTypeInformatieObjectType.objects.count(), 1)

    def test_create_with_external_informatieobjecttype_unknown_service(self):
        external = (
            f"https://unknown.documenten.nl/api/v1/informatieobjecttypen/{uuid.uuid4()}"
        )

        response = self.client.post(self.list_url, self._data([external]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            [param["code"] for param in response.json()["invalidParams"]],
            ["unknown-service"],
        )
        self.assertFalse(BesluitType.objects.exists())

    def test_create_with_second_external_informatieobjecttype_invalid(self):
        valid = new_external_iotype()
        invalid = new_external_iotype()

        with requests_mock.Mocker() as m:
            self.mock_external_iotype(m, valid)
            m.get(invalid, text="not json")
            response = self.client.post(self.list_url, self._data([valid, invalid]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttypen.1")
        self.assertEqual(error["code"], "invalid-resource")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakTypePublishExternalInformatieObjectTypeTests(
    ExternalInformatieObjectTypeMixin, TestCase
):
    def _validate(self, zaaktype, concept: bool | None = None, unavailable=False):
        iotype = zaaktype.zaaktypeinformatieobjecttype_set.get()._iotype_url
        with requests_mock.Mocker() as m:
            if unavailable:
                m.get(iotype, exc=requests.exceptions.ConnectTimeout("timed out"))
            elif concept is not None:
                self.mock_external_iotype(m, iotype, concept=concept)
            return [
                str(error) for _field, error in validate_zaaktype_for_publish(zaaktype)
            ]

    def _zaaktype(self) -> ZaakType:
        zaaktype = ZaakTypeFactory.create(concept=True)
        ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=new_external_iotype(),
            volgnummer=1,
            richting=RichtingChoices.inkomend,
        )
        return zaaktype

    def test_concept_external_informatieobjecttype(self):
        errors = self._validate(self._zaaktype(), concept=True)

        self.assertIn(str(RESOURCES_PUBLISHED_ERROR), errors)

    def test_published_external_informatieobjecttype(self):
        errors = self._validate(self._zaaktype(), concept=False)

        self.assertNotIn(str(RESOURCES_PUBLISHED_ERROR), errors)
        self.assertFalse(any("could not be retrieved" in error for error in errors))

    def test_unavailable_external_informatieobjecttype(self):
        errors = self._validate(self._zaaktype(), unavailable=True)

        self.assertTrue(any("could not be retrieved" in error for error in errors))

    def test_no_external_informatieobjecttypen_are_fetched(self):
        zaaktype = ZaakTypeFactory.create(concept=True)

        with requests_mock.Mocker():
            errors = [
                str(error) for _f, error in validate_zaaktype_for_publish(zaaktype)
            ]

        self.assertNotIn(str(RESOURCES_PUBLISHED_ERROR), errors)
