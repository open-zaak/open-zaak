# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from datetime import timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from openzaak.components.zaken.models import ZaakObject
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.notifications import default as handlers


@override_settings(ZAAK_NOTIFICATIONS_HANDLER="openzaak.notifications.default")
class NotificationHandlerTests(TestCase):
    def test_handle_create_adds_zaakobject(self):
        zaak = ZaakFactory()
        message = {
            "resource": "object",
            "actie": "create",
            "resourceUrl": "https://example.com/objecten/1",
            "kenmerken": {"objecttypeOmschrijving": "document"},
            "zaken": [zaak.pk],
        }

        handlers.handle(message)

        self.assertEqual(ZaakObject.objects.count(), 1)
        obj = ZaakObject.objects.first()
        self.assertEqual(obj.object, message["resourceUrl"])
        self.assertEqual(obj.zaak, zaak)
        self.assertEqual(obj.object_type_overige, "document")

    def test_handle_update_removes_unlinked_zaakobjects(self):
        resource_url = "https://example.com/objecten/1"
        zaak1 = ZaakFactory()
        zaak2 = ZaakFactory()
        obj1 = ZaakObject.objects.create(
            zaak=zaak1, object=resource_url, object_type="overig"
        )
        ZaakObject.objects.create(zaak=zaak2, object=resource_url, object_type="overig")

        message = {
            "resource": "object",
            "actie": "update",
            "resourceUrl": resource_url,
            "zaken": [zaak2.pk],
        }

        handlers.handle(message)

        remaining = list(ZaakObject.objects.values_list("zaak_id", flat=True))
        self.assertEqual(remaining, [zaak2.pk])
        self.assertFalse(ZaakObject.objects.filter(pk=obj1.pk).exists())

    def test_handle_destroy_deletes_objects(self):
        resource_url = "https://example.com/objecten/1"
        zaak = ZaakFactory()
        ZaakObject.objects.create(zaak=zaak, object=resource_url, object_type="overig")

        message = {
            "resource": "object",
            "actie": "destroy",
            "resourceUrl": resource_url,
        }

        handlers.handle(message)
        self.assertEqual(ZaakObject.objects.count(), 0)


@override_settings(
    ZAAK_NOTIFICATIONS_HANDLER="openzaak.notifications.default",
    REST_FRAMEWORK={
        "DEFAULT_PERMISSION_CLASSES": [],
        "DEFAULT_VERSION": 1,
    },
)
class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("zaak-notifications-callback", kwargs={"version": 1})

    @patch("openzaak.notifications.views.NotificationView.permission_classes", new=[])
    @patch("openzaak.notifications.default.handle")
    def test_post_calls_handler(self, mock_handle):
        from datetime import datetime

        """POSTing a valid notification should call the configured handler."""
        ZaakFactory()
        payload = {
            "resource": "object",
            "actie": "create",
            "resource_url": "https://example.com/objecten/1",
            "kenmerken": {"objecttype_omschrijving": "document"},
            "kanaal": "vrc",
            "hoofd_object": "https://example.com/objecten/1",
            "aanmaakdatum": datetime.now(tz=timezone.utc),
        }

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_handle.assert_called_once_with(payload)

    @patch("openzaak.notifications.views.NotificationView.permission_classes", new=[])
    @patch("openzaak.notifications.default.handle")
    def test_invalid_payload_returns_400(self, mock_handle):
        payload = {"invalid": "data"}

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_handle.assert_not_called()
