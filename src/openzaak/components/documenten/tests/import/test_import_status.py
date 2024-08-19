# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.test import override_settings, tag
from django.utils.translation import gettext as _

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
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.utils import ImportTestMixin
from openzaak.tests.utils import JWTAuthMixin


@tag("documenten-import-status")
class ImportDocumentenStatustTests(ImportTestMixin, JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    heeft_alle_autorisaties = True

    clean_documenten_files = True
    clean_import_files = True

    def test_active_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_successfully=125000,
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
                "processedSuccessfully": 125000,
                "processedInvalid": 125000,
                "status": ImportStatusChoices.active.value,
            },
        )

    def test_error_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.error,
            total=500000,
            processed=100000,
            processed_successfully=50000,
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
                "processedSuccessfully": 50000,
                "processedInvalid": 50000,
                "status": ImportStatusChoices.error.value,
            },
        )

    def test_finished_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.finished,
            total=500000,
            processed=250000,
            processed_successfully=125000,
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
                "processedSuccessfully": 125000,
                "processedInvalid": 125000,
                "status": ImportStatusChoices.finished.value,
            },
        )

    def test_pending_import(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=500000,
            processed=0,
            processed_successfully=0,
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
                "processedSuccessfully": 0,
                "processedInvalid": 0,
                "status": ImportStatusChoices.pending.value,
            },
        )

    def test_mismatching_import_type(self):
        import_instance = self.create_import(
            import_type="foobar",
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_successfully=125000,
            processed_invalid=125000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_alle_autorisaties(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_successfully=125000,
            processed_invalid=125000,
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
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")

    @override_settings(CMIS_ENABLED=True)
    def test_cmis_enabled(self):
        import_instance = self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=500000,
            processed=250000,
            processed_successfully=125000,
            processed_invalid=125000,
        )

        url = reverse(
            "documenten-import:status", kwargs=dict(uuid=import_instance.uuid)
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()

        self.assertEqual(response_data["code"], _("CMIS not supported"))
