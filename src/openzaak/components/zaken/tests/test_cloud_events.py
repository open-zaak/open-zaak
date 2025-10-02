# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from unittest.mock import patch

from django.test import override_settings

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse
from zgw_consumers.constants import AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ZaakTypeFactory,
)
from openzaak.config.models import CloudEventConfig
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin

from ..api import cloud_events
from ..api.cloud_events import (
    ZAAK_GEMUTEERD,
    ZAAK_GEOPEND,
    ZAAK_VERWIJDEREN,
)
from ..models import Zaak
from .factories import (
    ZaakFactory,
)
from .utils import (
    ZAAK_WRITE_KWARGS,
)


@freeze_time("2025-09-23T12:00:00Z")
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
        zaak = ZaakFactory.create()

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay",
            autospec=True,
        ) as mock_send:
            response = self.client.patch(
                reverse(zaak),
                {"toelichting": "Updated toelichting"},
                **ZAAK_WRITE_KWARGS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            self.assertIn("id", event_payload)

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEMUTEERD,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    def test_send_zaak_verwijderd_cloud_event(self, mock_get_solo):
        zaak = ZaakFactory.create()

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay",
            autospec=True,
        ) as mock_send:
            response = self.client.delete(
                reverse(zaak),
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_VERWIJDEREN,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    def test_send_zaak_geopend_cloud_event(self, mock_get_solo):
        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(
            uuid="4f2aa64b-eb42-491f-ba48-e27e8f66716c",
            catalogus=catalogus,
            concept=False,
        )

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay",
            autospec=True,
        ) as mock_send:
            zaaktype_url = reverse(zaaktype)

            response = self.client.post(
                reverse("zaak-list"),
                data={
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                format="json",
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_send.assert_called_once()

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            zaak = Zaak.objects.get(uuid=response.data["uuid"])

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEMUTEERD,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    def test_send_cloud_event_task_posts_expected_payload(self, mock_get_solo):
        service = ServiceFactory.create(
            api_root="http://webhook.local",
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foo",
        )

        zaak = ZaakFactory.create()

        mock_config = CloudEventConfig(
            enabled=True,
            source="urn:nld:oin:00000001823288444000:zakensysteem",
            webhook_service=service,
            webhook_path="/events",
        )
        mock_get_solo.return_value = mock_config

        event_id = str(uuid.uuid4())
        payload = {
            "specversion": "1.0",
            "type": ZAAK_GEOPEND,
            "source": "urn:nld:oin:00000001823288444000:zakensysteem",
            "subject": str(zaak.uuid),
            "dataref": reverse(zaak),
            "datacontenttype": "application/json",
            "data": {},
            "time": "2025-09-23T12:00:00Z",
            "id": event_id,
        }

        with requests_mock.Mocker() as m:
            m.post("http://webhook.local/events")

            cloud_events.send_cloud_event(payload)

        self.assertEqual(len(m.request_history), 1)

        request = m.request_history[0]

        self.assertEqual(request.url, "http://webhook.local/events")
        self.assertEqual(request.json(), payload)
        self.assertEqual(
            request.headers["content-type"], "application/cloudevents+json"
        )
        self.assertEqual(request.headers["Authorization"], "Token foo")
