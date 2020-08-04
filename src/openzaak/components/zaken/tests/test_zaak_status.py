# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.utils.tests import JWTAuthMixin

from .factories import StatusFactory, ZaakFactory
from .utils import ZAAK_READ_KWARGS


class ZaakStatusTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_read_zaak_with_status(self):
        """Test that the last status is shown in the Zaak request"""
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak)
        StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak)
        status_last = StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak)
        status_last_url = reverse(status_last)

        response = self.client.get(zaak_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["status"], f"http://testserver{status_last_url}")
