# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import tag

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.api.serializers import ReservedDocumentSerializer
from openzaak.components.documenten.api.utils import generate_document_identificatie
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    ReservedDocument,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
class ReservedDocumentTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("reserveddocument-list")
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.bronorganisatie = "812345678"
        self.reserved_identificatie = "DOCUMENT-2025-0000000001"
        self.new_identificatie = "DOCUMENT-2025-0000000002"
        self.another_reserved_identificatie = "DOCUMENT-2025-0000000003"

        self.reserved_document = ReservedDocument.objects.create(
            identificatie=self.reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        ReservedDocument.objects.create(
            identificatie=self.another_reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

    @tag("gh-2018")
    def test_reserved_document_str_representation(self):
        reserved_document = ReservedDocument.objects.create(
            identificatie="DOCUMENT-2025-1234567890",
            bronorganisatie="812345678",
        )
        expected_str = "812345678 - DOCUMENT-2025-1234567890"
        self.assertEqual(str(reserved_document), expected_str)

    @tag("gh-2018")
    def test_reserve_document_creates_successfully(self):
        reserved_document = ReservedDocument.objects.create(
            identificatie=self.new_identificatie, bronorganisatie=self.bronorganisatie
        )
        self.assertEqual(reserved_document.identificatie, self.new_identificatie)
        self.assertEqual(reserved_document.bronorganisatie, self.bronorganisatie)

    @tag("gh-2018")
    def test_generate_identificatie_excludes_reserved_and_issued_ids(self):
        generated_id = generate_document_identificatie(
            bronorganisatie=self.bronorganisatie,
            date_value=date.today(),
        )
        self.assertNotIn(generated_id, [self.reserved_identificatie])

    @tag("gh-2018")
    def test_create_enkelvoudig_info_object_with_reserved_identificatie(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie=self.reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )
        self.assertFalse(
            ReservedDocument.objects.filter(
                identificatie=self.reserved_identificatie,
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )

        self.assertEqual(eio.identificatie, self.reserved_identificatie)

    @tag("gh-2018")
    def test_create_reservation_when_no_identificatie_provided(self):
        data = {
            "bronorganisatie": self.bronorganisatie,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        reserved_doc = ReservedDocument.objects.get(
            identificatie=response.data["identificatie"],
            bronorganisatie=self.bronorganisatie,
        )

        self.assertIsNotNone(reserved_doc.identificatie)
        self.assertTrue(reserved_doc.identificatie.startswith("DOCUMENT-2025"))

    @tag("gh-2018")
    def test_identificatie_generation_excludes_all_taken_ids(self):
        issued_identificatie = "DOCUMENT-2025-0000000001"
        EnkelvoudigInformatieObjectFactory.create(
            identificatie=issued_identificatie,
            bronorganisatie=self.bronorganisatie,
        )
        ReservedDocument.objects.create(
            identificatie=self.reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        taken_ids = [self.reserved_identificatie, issued_identificatie]

        response = self.client.post(self.url, {"bronorganisatie": self.bronorganisatie})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_id = response.data["identificatie"]

        self.assertNotIn(new_id, taken_ids)

    @tag("gh-2018")
    def test_identificatie_is_generated_for_new_document(self):
        data = {
            "bronorganisatie": self.bronorganisatie,
        }

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        identificatie = response.data.get("identificatie")
        self.assertIsNotNone(identificatie)
        self.assertEqual(identificatie, "DOCUMENT-2025-0000000004")

        instance = ReservedDocument.objects.get(identificatie=identificatie)
        self.assertIsNotNone(instance)

    @tag("gh-2018")
    def test_create_reserved_document(self):
        data = {
            "bronorganisatie": "812345678",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("identificatie", response.json())
        self.assertEqual(ReservedDocument.objects.count(), 3)

    @tag("gh-2018")
    def test_create_reserved_document_creates_new_reservation(self):
        url = reverse("reserveddocument-list", kwargs={"version": "1"})

        response = self.client.post(
            url, {"bronorganisatie": self.bronorganisatie}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("identificatie", response.data)

        identificatie = response.data["identificatie"]
        self.assertTrue(identificatie.startswith(f"DOCUMENT-{date.today().year}-"))

        reserved = ReservedDocument.objects.get(
            identificatie=identificatie, bronorganisatie=self.bronorganisatie
        )
        self.assertIsNotNone(reserved)

    @tag("gh-2018")
    def test_serializer_creates_identificatie_when_missing(self):
        data = {"bronorganisatie": self.bronorganisatie}

        serializer = ReservedDocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

        instance = serializer.save()

        self.assertIsNotNone(instance.identificatie)
        self.assertTrue(
            instance.identificatie.startswith(f"DOCUMENT-{date.today().year}-")
        )

        self.assertTrue(ReservedDocument.objects.filter(id=instance.id).exists())


class EnkelvoudigInformatieObjectTests(JWTAuthMixin, APITestCase):
    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.bronorganisatie = "812345678"
        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        self.informatieobjecttype_url = reverse(self.informatieobjecttype)

    @tag("gh-2018")
    def test_post_without_identificatie_generates_unique_identificatie(self):
        EnkelvoudigInformatieObjectFactory.create(
            identificatie="DOCUMENT-2025-0000000001",
            bronorganisatie=self.bronorganisatie,
        )

        ReservedDocument.objects.create(
            identificatie="DOCUMENT-2025-0000000002",
            bronorganisatie=self.bronorganisatie,
        )

        data = {
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": date.today(),
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "informatieobjecttype": f"http://testserver{self.informatieobjecttype_url}",
        }

        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        identificatie = response.data["identificatie"]

        self.assertEqual(identificatie, "DOCUMENT-2025-0000000003")

    @tag("gh-2018")
    def test_post_with_reserved_identificatie_deletes_reserved_document(self):
        reserved_identificatie = "DOCUMENT-2025-0000000004"
        content = {
            "identificatie": reserved_identificatie,
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": date.today(),
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "informatieobjecttype": f"http://testserver{self.informatieobjecttype_url}",
        }

        response = self.client.post(self.list_url, content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["identificatie"], "DOCUMENT-2025-0000000004")

        self.assertFalse(
            ReservedDocument.objects.filter(
                identificatie=reserved_identificatie,
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )

        self.assertTrue(response.data.get("identificatie"), reserved_identificatie)

    @tag("gh-2018")
    def test_generated_identificatie_starts_from_one_when_none_exist(self):
        data = {
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": date.today(),
            "titel": "Start from one",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "informatieobjecttype": f"http://testserver{self.informatieobjecttype_url}",
        }

        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(response.data["identificatie"], "DOCUMENT-2025-0000000001")

        self.assertFalse(
            ReservedDocument.objects.filter(
                identificatie="DOCUMENT-2025-0000000001",
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )
