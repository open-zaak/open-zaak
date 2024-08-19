# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import override_settings, tag
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
    SCOPE_DOCUMENTEN_LOCK,
)
from openzaak.components.documenten.import_utils import DocumentRow
from openzaak.components.documenten.tests.factories import DocumentRowFactory
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.utils import (
    ImportTestMixin,
    get_csv_data,
    get_temporary_file,
)
from openzaak.tests.utils.auth import JWTAuthMixin


@tag("documenten-import-upload")
class ImportDocumentenUploadTests(ImportTestMixin, JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    heeft_alle_autorisaties = True

    clean_documenten_files = True
    clean_import_files = True

    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_valid_upload(self, import_document_task_mock):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]

        file_contents = get_csv_data(rows, DocumentRow.import_headers)
        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.active)

        import_path = Path(import_instance.import_file.path)

        with open(str(import_path), newline="") as import_file:
            self.assertEqual(file_contents, import_file.read())

        self.addCleanup(import_path.unlink)

        import_document_task_mock.delay.assert_called()

    def test_missing_headers(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        headers = DocumentRow.import_headers[1:]  # misses the uuid header
        rows = [DocumentRowFactory()]

        import_contents = get_csv_data(rows, headers)

        response = self.client.post(url, import_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "missing-import-headers")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_no_headers(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        headers = []
        rows = [DocumentRowFactory()]

        import_contents = get_csv_data(rows, headers)

        response = self.client.post(url, import_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "missing-import-headers")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_empty_csv_data(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.post(url, "", content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "empty-file")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_no_csv_file(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        data = bytes("%PDF-1.5%äðíø", encoding="latin-1")

        response = self.client.post(url, data, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = response.json()

        self.assertEqual(error_data["code"], "parse_error")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_invalid_content_type(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]

        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="application/pdf")

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_unknown_import(self):
        import_uuid = uuid4()

        url = reverse("documenten-import:upload", kwargs=dict(uuid=import_uuid))

        rows = [DocumentRowFactory()]

        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mismatching_import_type(self):
        import_instance = self.create_import(
            import_type="foobar",
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

    def test_active_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=249000,
            processed_successfully=125000,
            processed_invalid=124000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.active)

    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_existing_active_import(self, import_document_task_mock):
        self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=249000,
            processed_successfully=125000,
            processed_invalid=124000,
        )

        new_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=500000,
            processed=0,
            processed_successfully=0,
            processed_invalid=0,
        )

        url = reverse("documenten-import:upload", kwargs=dict(uuid=new_instance.uuid))

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        import_document_task_mock.assert_not_called()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "existing-import-started")

        new_instance.refresh_from_db()

        self.assertEqual(new_instance.status, ImportStatusChoices.pending)

    def test_error_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            total=500000,
            processed=249000,
            processed_successfully=125000,
            processed_invalid=124000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.error)

    def test_finished_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            total=500000,
            processed=500000,
            processed_successfully=250000,
            processed_invalid=250000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.finished)

    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_no_alle_autorisaties(self, import_document_task_mock):
        applicatie = self.applicatie

        applicatie.heeft_alle_autorisaties = False
        applicatie.save()

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=[
                SCOPE_DOCUMENTEN_AANMAKEN,
                SCOPE_DOCUMENTEN_BIJWERKEN,
                SCOPE_DOCUMENTEN_ALLES_LEZEN,
                SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
                SCOPE_DOCUMENTEN_LOCK,
                SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
            ],
            zaaktype="",
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

        import_document_task_mock.delay.assert_not_called()

    @override_settings(CMIS_ENABLED=True)
    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_cmis_enabled(self, import_document_task_mock):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory()]
        file_contents = get_csv_data(rows, DocumentRow.import_headers)

        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()

        self.assertEqual(response_data["code"], _("CMIS not supported"))

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)

        import_document_task_mock.delay.assert_not_called()

    @override_settings(IMPORT_DOCUMENTEN_BASE_DIR="/foobar/")
    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_import_dir_does_not_exist(self, import_document_task_mock):
        import_dir = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)

        self.assertFalse(import_dir.exists())

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            import_file=None,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory(ignore_import_path=True)]

        file_contents = get_csv_data(rows, DocumentRow.import_headers)
        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "import-dir-not-found")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)
        self.assertFalse(import_instance.import_file)

        import_document_task_mock.delay.assert_not_called()

    @patch("openzaak.components.documenten.api.viewsets.import_documents")
    def test_import_dir_is_file(self, import_document_task_mock):
        override = override_settings(IMPORT_DOCUMENTEN_BASE_DIR=get_temporary_file())
        override.enable()

        import_dir = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)

        self.assertTrue(import_dir.is_file())

        self.addCleanup(import_dir.unlink)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            import_file=None,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        rows = [DocumentRowFactory(ignore_import_path=True)]

        file_contents = get_csv_data(rows, DocumentRow.import_headers)
        response = self.client.post(url, file_contents, content_type="text/csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "import-dir-not-dir")

        import_instance.refresh_from_db()

        self.assertEqual(import_instance.status, ImportStatusChoices.pending)
        self.assertFalse(import_instance.import_file)

        import_document_task_mock.delay.assert_not_called()
