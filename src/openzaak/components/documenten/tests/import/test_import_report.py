from pathlib import Path

from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse

from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN
from openzaak.tests.utils import JWTAuthMixin
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.factories import ImportFactory


@tag("documenten-import-report")
class ImportDocumentenReportTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_AANMAKEN]
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.test_path = Path(__file__).parent.resolve() / "files"

    def test_simple(self):
        import_file_path = self.test_path / "import.csv"
        report_path = self.test_path / "import_report.csv"

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__from_path=import_file_path,
            report_file__from_path=report_path,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        with open(report_path, "rb") as report_file:
            self.assertEqual(response.getvalue(), report_file.read())

    def test_active_import(self):
        import_file_path = self.test_path / "import.csv"

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            import_file__from_path=import_file_path,
            report_file=None,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_error_import(self):
        import_file_path = self.test_path / "import.csv"
        report_path = self.test_path / "import_report_errors.csv"

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            import_file__from_path=import_file_path,
            report_file__from_path=report_path,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        with open(report_path, "rb") as report_file:
            self.assertEqual(response.getvalue(), report_file.read())

    def test_pending_import(self):
        import_file_path = self.test_path / "import.csv"
        report_path = self.test_path / "import_report.csv"

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__from_path=import_file_path,
            report_file__from_path=report_path,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_import_type_mismatch(self):
        import_file_path = self.test_path / "import.csv"
        report_path = self.test_path / "import_report.csv"

        import_instance = ImportFactory.create(
            import_type="foobar",
            status=ImportStatusChoices.finished,
            import_file__from_path=import_file_path,
            report_file__from_path=report_path,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_insufficient_scopes(self):
        import_file_path = self.test_path / "import.csv"
        report_path = self.test_path / "import_report.csv"

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__from_path=import_file_path,
            report_file__from_path=report_path,
            total=100000,
        )

        autorisatie = self.autorisatie

        autorisatie.scopes = []
        autorisatie.save()

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")
