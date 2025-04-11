# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin

from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS


class ZaakOpschortingTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_eerdere_opschorting_field_cannot_be_changed(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {
                "opschorting": {
                    "indicatie": True,
                    "eerdere_opschorting": False,
                    "reden": "test",
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["opschorting"],
            {"indicatie": True, "eerdere_opschorting": True, "reden": "test"},
        )

    def test_eerdere_opschorting_stays(self):
        zaak = ZaakFactory.create(opschorting_indicatie=True)

        self.assertTrue(zaak.opschorting_eerdere_opschorting)

        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"opschorting": {"indicatie": False, "reden": ""}},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["opschorting"],
            {"indicatie": False, "eerdere_opschorting": True, "reden": ""},
        )

    def test_eerdere_opschorting_stays_with_null(self):
        zaak = ZaakFactory.create(opschorting_indicatie=True)

        self.assertTrue(zaak.opschorting_eerdere_opschorting)

        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"opschorting": None},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["opschorting"],
            {"indicatie": False, "eerdere_opschorting": True, "reden": ""},
        )
