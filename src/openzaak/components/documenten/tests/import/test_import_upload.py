from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.tests.utils.auth import JWTAuthMixin
from openzaak.utils.models import ImportStatusChoices, ImportTypeChoices
from openzaak.utils.tests.factories import ImportFactory


@tag("documenten-import-upload")
class ImportDocumentenUploadTests(JWTAuthMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.test_path = Path(__file__).parent.resolve() / "files"

    # TODO: add more in depth testing (assert updated import instance, EIO instance,
    # saved file contents)
    def test_valid_upload(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_headers(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import_missing_headers.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "missing-import-headers")

    def test_no_headers(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import_no_headers.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "missing-import-headers")

    def test_empty_csv_data(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.post(
            url, bytes("", settings.DEFAULT_CHARSET), content_type="text/csv"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "missing-import-headers")

    def test_no_csv_file(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "empty.pdf", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = response.json()

        self.assertEqual(error_data["code"], "parse_error")

    def test_invalid_content_type(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="application/pdf"
            )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_validation_errors(self):
        raise NotImplementedError

    def test_unknown_import(self):
        import_uuid = uuid4()

        url = reverse("documenten-import:upload", kwargs=dict(uuid=import_uuid))

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mismatching_import_type(self):
        import_instance = ImportFactory.create(
            import_type="foobar", status=ImportStatusChoices.pending, total=0,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_active_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=249000,
            processed_succesfully=125000,
            processed_invalid=124000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

    def test_error_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            total=500000,
            processed=249000,
            processed_succesfully=125000,
            processed_invalid=124000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

    def test_finished_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            total=500000,
            processed=500000,
            processed_succesfully=250000,
            processed_invalid=250000,
        )

        url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=import_instance.uuid)
        )

        with open(self.test_path / "import.csv", "rb") as import_file:
            response = self.client.post(
                url, import_file.read(), content_type="text/csv"
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "__all__")

        self.assertEqual(validation_error["code"], "invalid-status")

    def test_database_connection_loss(self):
        raise NotImplementedError
