from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.utils.tests.factories import ImportFactory


@tag("documenten-import-start")
class ImportDocumentenStartTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("documenten-import:start")

    def test_simple(self):
        response = self.client.post(self.url)

        instance = Import.objects.get()

        self.assertEqual(instance.status, ImportStatusChoices.pending)
        self.assertEqual(instance.import_type, ImportTypeChoices.documents)

        upload_url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=str(instance.uuid))
        )
        status_url = reverse(
            "documenten-import:status", kwargs=dict(uuid=str(instance.uuid))
        )
        report_url = reverse(
            "documenten-import:report", kwargs=dict(uuid=str(instance.uuid))
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "uploadUrl": f"http://testserver{upload_url}",
                "statusUrl": f"http://testserver{status_url}",
                "reportUrl": f"http://testserver{report_url}",
            },
        )

    def test_existing_active_import(self):
        ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=123,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "__all__")
        self.assertEqual(error["code"], "existing-import-started")

    def test_existing_pending_import(self):
        ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=123,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "__all__")
        self.assertEqual(error["code"], "existing-import-started")
