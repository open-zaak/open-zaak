from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.models import ImportStatusChoices, ImportTypeChoices
from openzaak.utils.tests.factories import ImportFactory


@tag("documenten-import-status")
class ImportDocumentenStatustTests(JWTAuthMixin, APITestCase):
    def test_active_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_succesfully=125000,
            processed_invalid=125000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "total": 500000,
                "processed": 250000,
                "processedSuccesfully": 125000,
                "processedInvalid": 125000,
                "status": ImportStatusChoices.active.label,
            },
        )

    def test_error_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            total=500000,
            processed=100000,
            processed_succesfully=50000,
            processed_invalid=50000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "total": 500000,
                "processed": 100000,
                "processedSuccesfully": 50000,
                "processedInvalid": 50000,
                "status": ImportStatusChoices.error.label,
            },
        )

    def test_finished_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            total=500000,
            processed=250000,
            processed_succesfully=125000,
            processed_invalid=125000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "total": 500000,
                "processed": 250000,
                "processedSuccesfully": 125000,
                "processedInvalid": 125000,
                "status": ImportStatusChoices.finished.label,
            },
        )

    def test_pending_import(self):
        import_instance = ImportFactory.create(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=500000,
            processed=0,
            processed_succesfully=0,
            processed_invalid=0,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "total": 500000,
                "processed": 0,
                "processedSuccesfully": 0,
                "processedInvalid": 0,
                "status": ImportStatusChoices.pending.label,
            },
        )

    def test_mismatching_import_type(self):
        import_instance = ImportFactory.create(
            import_type="foobar",
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_succesfully=125000,
            processed_invalid=125000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
