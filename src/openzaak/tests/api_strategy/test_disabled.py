# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse

from openzaak.components.zaken.tests.utils import ZAAK_READ_KWARGS
from openzaak.config.models import InternalService
from openzaak.utils.tests import JWTAuthMixin


class DisableTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def _test_service_disabled(self, component_type, url, **kwargs):
        # service is enabled
        response = self.client.get(url, **kwargs)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # service is disabled
        service, created = InternalService.objects.get_or_create(
            api_type=component_type
        )
        service.enabled = False
        service.save()

        response = self.client.get(url, **kwargs)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_zaken(self):
        self._test_service_disabled(
            ComponentTypes.zrc, reverse("zaak-list"), **ZAAK_READ_KWARGS
        )

    def test_catalogi(self):
        self._test_service_disabled(ComponentTypes.ztc, reverse("zaaktype-list"))

    def test_besluiten(self):
        self._test_service_disabled(ComponentTypes.brc, reverse("besluit-list"))

    def test_documenten(self):
        self._test_service_disabled(
            ComponentTypes.drc, reverse("enkelvoudiginformatieobject-list")
        )

    def test_authorisaties(self):
        self._test_service_disabled(ComponentTypes.ac, reverse("applicatie-list"))
