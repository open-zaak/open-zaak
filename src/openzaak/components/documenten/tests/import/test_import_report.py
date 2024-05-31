from django.conf import settings
from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse

from openzaak.accounts.tests.factories import UserFactory
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN
from openzaak.components.documenten.tests.factories import DocumentRowReportFactory, DocumentRowFactory
from openzaak.components.documenten.utils import DocumentRow
from openzaak.import_data.tests.utils import get_csv_data
from openzaak.tests.utils import JWTAuthMixin
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.factories import ImportFactory


@tag("documenten-import-report")
class ImportDocumentenReportTests(JWTAuthMixin, APITestCase):
    def test_simple(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        response_data = response.getvalue().decode(settings.DEFAULT_CHARSET)

        with open(import_instance.report_file.path, "r", newline="") as report_file:
            self.assertEqual(response_data, report_file.read())

    def test_active_import(self):
        rows = [DocumentRowFactory()]
        import_data = get_csv_data(rows, DocumentRow.import_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            import_file__data=import_data,
            report_file=None,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_error_import(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        response_data = response.getvalue().decode(settings.DEFAULT_CHARSET)

        with open(import_instance.report_file.path, "r", newline="") as report_file:
            self.assertEqual(response_data, report_file.read())

    def test_pending_import(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_import_type_mismatch(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type="foobar",
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_regular_user(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")

    def test_admin_user(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data([DocumentRowReportFactory()], DocumentRow.export_headers)

        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        autorisatie = self.autorisatie

        autorisatie.scopes = []
        autorisatie.save()

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        user = UserFactory.create(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")
