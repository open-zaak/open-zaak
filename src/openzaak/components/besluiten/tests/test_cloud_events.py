# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime

from django.test import override_settings, tag
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.zaken.api.cloudevents import ZAAK_GEMUTEERD
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.components.zaken.tests.test_cloud_events import (
    CloudEventSettingMixin,
    patch_send_cloud_event,
)
from openzaak.tests.utils import JWTAuthMixin

from ..models import Besluit
from .factories import BesluitFactory


@tag("cloudevents")
@override_settings(SITE_DOMAIN="testserver")
class BesluitCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.besluittype = BesluitTypeFactory.create(
            zaaktypen=[cls.zaak.zaaktype], concept=False
        )

        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "besluittype": f"http://testserver{reverse(cls.besluittype)}",
            "ingangsdatum": "2025-01-02",
            "datum": "2025-01-01",
            "verantwoordelijkeOrganisatie": "000000000",
        }

    def test_besluit_create_sends_gemuteerd_cloud_event_if_related_to_zaak(self):
        # Create without linking besluit to zaak should not emit `zaak-gemuteerd`
        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        reverse(Besluit),
                        {
                            "besluittype": f"http://testserver{reverse(self.besluittype)}",
                            "ingangsdatum": "2025-01-02",
                            "datum": "2025-01-01",
                            "verantwoordelijkeOrganisatie": "000000000",
                        },
                    )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        mock_send.assert_not_called()

        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(reverse(Besluit), self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assert_cloud_event_sent(
            ZAAK_GEMUTEERD, self.zaak, mock_send, timestamp="2025-09-23T12:15:00Z"
        )
        self.zaak.refresh_from_db()
        self.assertEqual(
            self.zaak.laatst_gemuteerd,
            timezone.make_aware(datetime(2025, 9, 23, 12, 15, 0)),
        )

    def test_besluit_update_sends_gemuteerd_cloud_event_if_related_to_zaak(self):
        # Updates without linking besluit to zaak should not emit `zaak-gemuteerd`
        besluit_without_zaak = BesluitFactory.create(
            zaak=None,
            besluittype=self.besluittype,
            verantwoordelijke_organisatie="000000000",
        )
        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.put(
                        reverse(besluit_without_zaak),
                        {
                            "besluittype": f"http://testserver{reverse(self.besluittype)}",
                            "ingangsdatum": "2025-01-02",
                            "datum": "2025-01-01",
                            "verantwoordelijkeOrganisatie": "000000000",
                        },
                    )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            mock_send.assert_not_called()

            with freeze_time("2025-09-23T12:16:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.patch(
                        reverse(besluit_without_zaak), {"datum": "2024-01-01"}
                    )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            mock_send.assert_not_called()

        besluit = BesluitFactory.create(
            zaak=self.zaak,
            besluittype=self.besluittype,
            verantwoordelijke_organisatie="000000000",
        )
        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.put(reverse(besluit), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(
                ZAAK_GEMUTEERD, self.zaak, mock_send, timestamp="2025-09-23T12:15:00Z"
            )
            self.zaak.refresh_from_db()
            self.assertEqual(
                self.zaak.laatst_gemuteerd,
                timezone.make_aware(datetime(2025, 9, 23, 12, 15, 0)),
            )

            mock_send.reset_mock()

            with freeze_time("2025-09-23T12:16:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.patch(reverse(besluit), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(
                ZAAK_GEMUTEERD, self.zaak, mock_send, timestamp="2025-09-23T12:16:00Z"
            )
            self.zaak.refresh_from_db()
            self.assertEqual(
                self.zaak.laatst_gemuteerd,
                timezone.make_aware(datetime(2025, 9, 23, 12, 16, 0)),
            )

    def test_besluit_destroy_sends_gemuteerd_cloud_event_if_related_to_zaak(self):
        # Deletes without linking besluit to zaak should not emit `zaak-gemuteerd`
        besluit_without_zaak = BesluitFactory.create(
            zaak=None, besluittype=self.besluittype
        )
        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.delete(reverse(besluit_without_zaak))

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        mock_send.assert_not_called()

        besluit = BesluitFactory.create(zaak=self.zaak, besluittype=self.besluittype)
        with patch_send_cloud_event() as mock_send:
            with freeze_time("2025-09-23T12:15:00Z"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.delete(reverse(besluit))

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assert_cloud_event_sent(
            ZAAK_GEMUTEERD, self.zaak, mock_send, timestamp="2025-09-23T12:15:00Z"
        )
        self.zaak.refresh_from_db()
        self.assertEqual(
            self.zaak.laatst_gemuteerd,
            timezone.make_aware(datetime(2025, 9, 23, 12, 15, 0)),
        )
