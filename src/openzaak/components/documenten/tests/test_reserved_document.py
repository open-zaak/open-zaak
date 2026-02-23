# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import tag

from freezegun import freeze_time
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.api.utils import generate_document_identificatie
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    ReservedDocument,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin


@tag("gh-2018")
@temp_private_root()
@freeze_time("2025-01-01T12:00:00")
class ReservedDocumentTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("reserveddocument-list")
    heeft_alle_autorisaties = True
    bronorganisatie = "812345678"

    def test_reserved_document_str_representation(self):
        reserved_document = ReservedDocument.objects.create(
            identificatie="DOCUMENT-2025-1234567890",
            bronorganisatie=self.bronorganisatie,
        )
        expected_str = "812345678 - DOCUMENT-2025-1234567890"
        self.assertEqual(str(reserved_document), expected_str)

    def test_reserve_document_creates_successfully(self):
        identificatie = "DOCUMENT-2025-0000000001"
        reserved_document = ReservedDocument.objects.create(
            identificatie=identificatie, bronorganisatie=self.bronorganisatie
        )
        self.assertEqual(reserved_document.identificatie, identificatie)
        self.assertEqual(reserved_document.bronorganisatie, self.bronorganisatie)

    def test_generate_identificatie_excludes_reserved_and_issued_ids(self):
        ReservedDocument.objects.create(
            identificatie="DOCUMENT-2025-0000000001",
            bronorganisatie=self.bronorganisatie,
        )
        EnkelvoudigInformatieObjectFactory.create(
            identificatie="DOCUMENT-2025-0000000002",
            bronorganisatie=self.bronorganisatie,
        )

        generated_id = generate_document_identificatie(
            bronorganisatie=self.bronorganisatie,
            date_value=date.today(),
        )
        self.assertNotIn(
            generated_id, ["DOCUMENT-2025-0000000001", "DOCUMENT-2025-0000000002"]
        )
        self.assertEqual(generated_id, "DOCUMENT-2025-0000000003")

    def test_create_enkelvoudig_info_object_with_reserved_identificatie(self):
        identificatie = "DOCUMENT-2025-0000000003"
        ReservedDocument.objects.create(
            identificatie=identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie=identificatie,
            bronorganisatie=self.bronorganisatie,
        )
        self.assertFalse(
            ReservedDocument.objects.filter(
                identificatie=identificatie,
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )

        self.assertEqual(eio.identificatie, identificatie)

    def test_create_reservation_when_no_identificatie_provided(self):
        data = {
            "bronorganisatie": self.bronorganisatie,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        identificatie = response.data["identificatie"]
        reserved_doc = ReservedDocument.objects.get(
            identificatie=identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        self.assertIsNotNone(reserved_doc.identificatie)
        self.assertTrue(reserved_doc.identificatie.startswith("DOCUMENT-2025"))

    def test_identificatie_generation_excludes_all_taken_ids(self):
        issued_identificatie = "DOCUMENT-2025-0000000001"
        reserved_identificatie = "DOCUMENT-2025-0000000002"

        EnkelvoudigInformatieObjectFactory.create(
            identificatie=issued_identificatie,
            bronorganisatie=self.bronorganisatie,
        )
        ReservedDocument.objects.create(
            identificatie=reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

        taken_ids = [reserved_identificatie, issued_identificatie]

        response = self.client.post(self.url, {"bronorganisatie": self.bronorganisatie})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_id = response.data["identificatie"]

        self.assertNotIn(new_id, taken_ids)
        self.assertEqual(new_id, "DOCUMENT-2025-0000000003")

    def test_create_reserved_document_and_validate_response_and_db(self):
        data = {
            "bronorganisatie": self.bronorganisatie,
        }

        url = reverse("reserveddocument-list", kwargs={"version": "1"})

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_data = response.data
        self.assertIn("identificatie", response_data)
        identificatie = response_data["identificatie"]
        self.assertIsNotNone(identificatie)
        self.assertTrue(identificatie.startswith(f"DOCUMENT-{date.today().year}-"))

        self.assertEqual(ReservedDocument.objects.count(), 1)

        reserved = ReservedDocument.objects.get(
            identificatie=identificatie,
            bronorganisatie=self.bronorganisatie,
        )
        self.assertIsNotNone(reserved)

    @freeze_time("2025-01-01")
    def test_create_multiple_reservations(self):
        data = {"bronorganisatie": self.bronorganisatie, "aantal": 3}

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        results = response.data
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)

        expected_ids = [
            "DOCUMENT-2025-0000000001",
            "DOCUMENT-2025-0000000002",
            "DOCUMENT-2025-0000000003",
        ]
        actual_ids = [item["identificatie"] for item in results]

        self.assertEqual(actual_ids, expected_ids)

        for identificatie in expected_ids:
            self.assertTrue(
                ReservedDocument.objects.filter(
                    identificatie=identificatie,
                    bronorganisatie=self.bronorganisatie,
                ).exists()
            )

    def test_create_reservation_with_invalid_amount(self):
        data = {"bronorganisatie": self.bronorganisatie, "aantal": 0}

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invalid_params = response.data.get("invalid_params", [])
        self.assertTrue(any(param.get("name") == "aantal" for param in invalid_params))


@freeze_time("2025-01-01T12:00:00")
@tag("gh-2018")
class EnkelvoudigInformatieObjectTests(JWTAuthMixin, APITestCase):
    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    heeft_alle_autorisaties = True
    bronorganisatie = "812345678"

    def setUp(self):
        super().setUp()
        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        self.informatieobjecttype_url = reverse(self.informatieobjecttype)

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

    def test_post_with_reserved_identificatie_deletes_reserved_document(self):
        reserved_identificatie = "DOCUMENT-2025-0000000004"

        ReservedDocument.objects.create(
            identificatie=reserved_identificatie,
            bronorganisatie=self.bronorganisatie,
        )

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
        self.assertEqual(response.data["identificatie"], reserved_identificatie)

        self.assertFalse(
            ReservedDocument.objects.filter(
                identificatie=reserved_identificatie,
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )

        self.assertEqual(response.data.get("identificatie"), "DOCUMENT-2025-0000000004")

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
