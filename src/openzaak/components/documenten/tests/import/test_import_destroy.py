# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.test import override_settings, tag
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.utils import ImportTestMixin
from openzaak.tests.utils import JWTAuthMixin


@tag("documenten-import-delete")
class ImportDocumentenDestroyTests(ImportTestMixin, JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    heeft_alle_autorisaties = True

    clean_documenten_files = True
    clean_import_files = True

    def test_pending_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=0,
        )

        url = reverse(
            "documenten-import:destroy", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Import.objects.count(), 0)

    def test_finished_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            total=10000,
        )

        url = reverse(
            "documenten-import:destroy", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Import.objects.count(), 0)

    def test_error_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            total=10000,
        )

        url = reverse(
            "documenten-import:destroy", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Import.objects.count(), 0)

    def test_active_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=10000,
        )

        url = reverse(
            "documenten-import:destroy", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Import.objects.count(), 1)

        error = get_validation_errors(response, "__all__")

        self.assertEqual(error["code"], "import-invalid-status")

    @override_settings(CMIS_ENABLED=True)
    def test_cmis_enabled(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=10000,
        )

        url = reverse(
            "documenten-import:destroy", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Import.objects.count(), 1)

        response_data = response.json()

        self.assertEqual(response_data["code"], _("CMIS not supported"))
