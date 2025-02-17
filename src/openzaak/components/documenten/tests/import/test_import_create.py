# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact

from django.contrib.sites.models import Site
from django.test import override_settings, tag
from django.utils.translation import gettext as _

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
    SCOPE_DOCUMENTEN_LOCK,
)
from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.tests.utils import ImportTestMixin
from openzaak.tests.utils import JWTAuthMixin


@temp_private_root()
@tag("documenten-import-start")
class ImportDocumentenCreateTests(ImportTestMixin, JWTAuthMixin, APITestCase):
    url = reverse_lazy("documenten-import:create")

    clean_documenten_files = True
    clean_import_files = True

    component = ComponentTypes.drc
    heeft_alle_autorisaties = True

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

        site = Site.objects.get_current()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "uploadUrl": f"http://{site.domain}{upload_url}",
                "statusUrl": f"http://{site.domain}{status_url}",
                "reportUrl": f"http://{site.domain}{report_url}",
            },
        )

    def test_existing_active_import(self):
        self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.active,
            total=123,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "__all__")
        self.assertEqual(error["code"], "existing-import-started")

    def test_existing_pending_import(self):
        self.create_import(
            import_type=ImportTypeChoices.documents,
            status=ImportStatusChoices.pending,
            total=123,
        )

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "__all__")
        self.assertEqual(error["code"], "existing-import-started")

    def test_no_alle_autorisaties(self):
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

        response = self.client.post(self.url)

        self.assertEqual(Import.objects.count(), 0)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response_data = response.json()

        self.assertEqual(response_data["code"], "permission_denied")

    @override_settings(CMIS_ENABLED=True)
    def test_cmis_enabled(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()

        self.assertEqual(response_data["code"], _("CMIS not supported"))
