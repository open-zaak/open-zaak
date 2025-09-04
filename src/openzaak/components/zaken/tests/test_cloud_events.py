# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
from unittest.mock import MagicMock, patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ZaakTypeFactory,
)
from openzaak.config.models import CloudEventConfig
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin

from ..api.cloud_events import ZAAK_GEMUTEERD, ZAAK_GEOPEND, ZAAK_VERWIJDERN
from ..models import Zaak
from .factories import (
    ZaakFactory,
)
from .utils import (
    ZAAK_WRITE_KWARGS,
)


@override_settings(ENABLE_CLOUD_EVENTS=True)
@patch(
    "openzaak.components.zaken.api.cloud_events.CloudEventConfig.get_solo",
    return_value=CloudEventConfig(
        enabled=True,
        source="urn:nld:oin:00000001823288444000:zakensysteem",
    ),
)
class CloudEventTests(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_send_zaak_gemuteerd_cloud_event(self, mock_get_solo):
        mock_config = MagicMock()
        mock_config.source = "urn:nld:oin:00000001823288444000:zakensysteem"
        mock_get_solo.return_value = mock_config

        zaak = ZaakFactory.create()
        reverse(zaak)

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay"
        ) as mock_send:
            response = self.client.patch(
                reverse(zaak),
                json={"toelichting": "Updated toelichting"},
                content_type="application/json",
                **ZAAK_WRITE_KWARGS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args
            event_payload = args[0]

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)
            event_payload_copy.pop("time", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEMUTEERD,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)
            self.assertIn("time", event_payload)

    def test_send_zaak_verwijderd_cloud_event(self, mock_get_solo):
        mock_config = MagicMock()
        mock_config.source = "urn:nld:oin:00000001823288444000:zakensysteem"
        mock_get_solo.return_value = mock_config

        zaak = ZaakFactory.create()

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay"
        ) as mock_send:
            response = self.client.delete(
                reverse(zaak),
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args
            event_payload = args[0]

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)
            event_payload_copy.pop("time", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_VERWIJDERN,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)
            self.assertIn("time", event_payload)

    def test_send_zaak_geopend_cloud_event(self, mock_get_solo):
        mock_config = MagicMock()
        mock_config.source = "urn:nld:oin:00000001823288444000:zakensysteem"
        mock_get_solo.return_value = mock_config

        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(
            uuid="4f2aa64b-eb42-491f-ba48-e27e8f66716c",
            catalogus=catalogus,
            concept=False,
        )

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay"
        ) as mock_send:
            zaaktype_url = reverse(zaaktype)

            response = self.client.post(
                reverse("zaak-list"),
                data=json.dumps(
                    {
                        "zaaktype": f"http://testserver{zaaktype_url}",
                        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                        "bronorganisatie": "517439943",
                        "verantwoordelijkeOrganisatie": "517439943",
                        "registratiedatum": "2018-12-24",
                        "startdatum": "2018-12-24",
                        "productenOfDiensten": ["https://example.com/product/123"],
                    }
                ),
                content_type="application/json",
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args
            event_payload = args[0]

            zaak = Zaak.objects.get(uuid=response.data["uuid"])

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)
            event_payload_copy.pop("time", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEOPEND,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)
            self.assertIn("time", event_payload)
