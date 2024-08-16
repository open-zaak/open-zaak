# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.conf import settings
from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
    SCOPE_DOCUMENTEN_LOCK,
)
from openzaak.components.documenten.import_utils import DocumentRow
from openzaak.components.documenten.tests.factories import (
    DocumentRowFactory,
    DocumentRowReportFactory,
)
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.utils import ImportTestMixin, get_csv_data
from openzaak.tests.utils import JWTAuthMixin


@tag("documenten-import-report")
class ImportDocumentenReportTests(ImportTestMixin, JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    heeft_alle_autorisaties = True

    clean_documenten_files = True
    clean_import_files = True

    def test_simple(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data(
            [DocumentRowReportFactory()], DocumentRow.export_headers
        )

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        response_data = response.getvalue().decode(settings.DEFAULT_CHARSET)

        with open(import_instance.report_file.path, newline="") as report_file:
            self.assertEqual(response_data, report_file.read())

    def test_active_import(self):
        rows = [DocumentRowFactory()]
        import_data = get_csv_data(rows, DocumentRow.import_headers)

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            import_file__data=import_data,
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
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data(
            [DocumentRowReportFactory()], DocumentRow.export_headers
        )

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

        response_data = response.getvalue().decode(settings.DEFAULT_CHARSET)

        with open(import_instance.report_file.path, newline="") as report_file:
            self.assertEqual(response_data, report_file.read())

    def test_pending_import(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data(
            [DocumentRowReportFactory()], DocumentRow.export_headers
        )

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_import_type_mismatch(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data(
            [DocumentRowReportFactory()], DocumentRow.export_headers
        )

        import_instance = self.create_import(
            import_type="foobar",
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotEqual(response["Content-Type"], "text/csv")

    def test_no_alle_autorisaties(self):
        import_data = get_csv_data([DocumentRowFactory()], DocumentRow.import_headers)
        report_data = get_csv_data(
            [DocumentRowReportFactory()], DocumentRow.export_headers
        )

        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            import_file__data=import_data,
            report_file__data=report_data,
            total=100000,
        )

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

        url = reverse(
            "documenten-import:report", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")
