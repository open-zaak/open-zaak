# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import TestCase
from django.urls import reverse

from rest_framework.exceptions import ValidationError

from openzaak.components.documenten.api.serializers import ReservedDocumentSerializer
from openzaak.components.documenten.api.utils import generate_document_identificatie
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    ReservedDocument,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)


class ReservedDocumentTests(TestCase):

    def setUp(self):
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

    def test_reserved_document_str_representation(self):
        reserved_document = ReservedDocument.objects.create(
            identificatie="DOCUMENT-2025-1234567890",
            bronorganisatie="812345678",
        )
        expected_str = "812345678 - DOCUMENT-2025-1234567890"
        self.assertEqual(str(reserved_document), expected_str)

    def test_reserve_document_creates_successfully(self):
        reserved_document = ReservedDocument.objects.create(
            identificatie=self.new_identificatie, bronorganisatie=self.bronorganisatie
        )
        self.assertEqual(reserved_document.identificatie, self.new_identificatie)
        self.assertEqual(reserved_document.bronorganisatie, self.bronorganisatie)

    def test_generate_identificatie_excludes_reserved_and_issued_ids(self):
        generated_id = generate_document_identificatie(
            bronorganisatie=self.bronorganisatie,
            document_model=EnkelvoudigInformatieObject,
            date_value=date.today(),
        )
        self.assertNotIn(generated_id, [self.reserved_identificatie])

    def test_create_enkelvoudig_info_object_with_reserved_identificatie(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie=self.reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        with self.assertRaises(ReservedDocument.DoesNotExist):
            ReservedDocument.objects.get(
                identificatie=self.reserved_identificatie,
                bronorganisatie=self.bronorganisatie,
            )

        self.assertEqual(eio.identificatie, self.reserved_identificatie)

    def test_create_enkelvoudig_info_object_with_non_reserved_identificatie(self):

        non_reserved_identificatie = "DOCUMENT-2022-0000900000"
        data = {
            "identificatie": non_reserved_identificatie,
            "bronorganisatie": self.bronorganisatie,
        }

        with self.assertRaises(ValidationError):

            serializer = ReservedDocumentSerializer(data=data)
            serializer.is_valid(raise_exception=True)

    def test_create_reservation_when_no_identificatie_provided(self):

        data = {
            "bronorganisatie": self.bronorganisatie,
        }

        serializer = ReservedDocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        reserved_doc = serializer.save()

        self.assertIsNotNone(reserved_doc.identificatie)
        self.assertTrue(reserved_doc.identificatie.startswith("DOCUMENT-2025"))

    def test_identificatie_generation_excludes_all_taken_ids(self):
        issued_identificatie = "DOCUMENT-2025-0000000001"
        taken_ids = [self.reserved_identificatie, issued_identificatie]
        new_id = generate_document_identificatie(
            bronorganisatie=self.bronorganisatie,
            document_model=EnkelvoudigInformatieObject,
            date_value=date.today(),
        )

        self.assertNotIn(new_id, taken_ids)

    def test_identificatie_is_generated_for_new_document(self):
        instance = EnkelvoudigInformatieObjectFactory.create(identificatie=None)

        assert instance.identificatie is not None
        assert instance.identificatie.startswith("DOCUMENT-" + str(date.today().year))
        assert len(instance.identificatie.split("-")[-1]) == 10

    def test_validate_identificatie_returns_value_when_reserved(self):
        data = {
            "identificatie": self.another_reserved_identificatie,
            "bronorganisatie": self.bronorganisatie,
        }

        serializer = ReservedDocumentSerializer(data=data)
        returned_value = serializer.validate_identificatie(data["identificatie"])

        self.assertEqual(returned_value, data["identificatie"])

    def test_create_reserved_document(self):
        url = reverse("reserveddocument-list", kwargs={"version": "1"})
        data = {
            "bronorganisatie": "812345678",
        }

        response = self.client.post(url, data, content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("identificatie", response.json())
        self.assertEqual(ReservedDocument.objects.count(), 3)

    def tearDown(self):
        ReservedDocument.objects.all().delete()
