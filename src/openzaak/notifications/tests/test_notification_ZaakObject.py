# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact

from unittest import mock

from django.test import TestCase

from openzaak.components.zaken.models import ZaakObject
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.notifications import handler_objecten as handlers

resource_url = (
    "https://objects.local/api/v2/objects/a28ac59d-31bb-43bf-9ded-c50d8e5f2654"
)


class NotificationHandlerTests(TestCase):
    @mock.patch(
        "openzaak.notifications.handler_objecten.BaseLoader.is_local_url",
        return_value=True,
    )
    @mock.patch("openzaak.notifications.handler_objecten.BaseLoader.load_local_object")
    def test_handle_create_adds_zaakobject(self, mock_load, mock_is_local):
        zaak = ZaakFactory()
        mock_load.return_value = zaak

        base_url = "https://openzaak.example.com/api/v1/zaken/"
        message = {
            "resource": "object",
            "actie": "create",
            "resourceUrl": "https://objects.local/api/v2/objects/a28ac59d-31bb-43bf-9ded-c50d8e5f2654",
            "kenmerken": {"objecttypeOmschrijving": "document"},
            "zaken": [f"{base_url}{zaak.pk}/"],
            "kanaal": "objecten",
        }

        handlers.handle(message)

        self.assertEqual(ZaakObject.objects.count(), 1)
        obj = ZaakObject.objects.first()
        self.assertEqual(obj.object, message["resourceUrl"])
        self.assertEqual(obj.zaak, zaak)
        self.assertEqual(obj.object_type_overige, "document")

    @mock.patch(
        "openzaak.notifications.handler_objecten.BaseLoader.is_local_url",
        return_value=True,
    )
    @mock.patch("openzaak.notifications.handler_objecten.BaseLoader.load_local_object")
    def test_handle_create_existing_relation(self, mock_load, mock_is_local):
        zaak = ZaakFactory()
        mock_load.return_value = zaak

        ZaakObject.objects.create(
            zaak=zaak,
            object=resource_url,
            object_type="overig",
        )

        base_url = "https://openzaak.example.com/api/v1/zaken/"
        message = {
            "resource": "object",
            "actie": "create",
            "resourceUrl": resource_url,
            "kenmerken": {"objecttypeOmschrijving": "document"},
            "zaken": [f"{base_url}{zaak.pk}/"],
            "kanaal": "objecten",
        }

        handlers.handle(message)

        self.assertEqual(ZaakObject.objects.count(), 1)
        obj = ZaakObject.objects.first()
        self.assertEqual(obj.zaak, zaak)
        self.assertEqual(obj.object, resource_url)

    @mock.patch(
        "openzaak.notifications.handler_objecten.BaseLoader.is_local_url",
        return_value=True,
    )
    @mock.patch("openzaak.notifications.handler_objecten.BaseLoader.load_local_object")
    def test_handle_update_removes_unlinked_zaakobjects(self, mock_load, mock_is_local):
        zaak1 = ZaakFactory()
        zaak2 = ZaakFactory()
        obj1 = ZaakObject.objects.create(
            zaak=zaak1, object=resource_url, object_type="overig"
        )
        ZaakObject.objects.create(zaak=zaak2, object=resource_url, object_type="overig")

        mock_load.return_value = zaak2
        base_url = "https://openzaak.example.com/api/v1/zaken/"
        message = {
            "resource": "object",
            "actie": "update",
            "resourceUrl": resource_url,
            "zaken": [f"{base_url}{zaak2.pk}/"],
            "kanaal": "objecten",
        }

        handlers.handle(message)

        remaining = list(ZaakObject.objects.values_list("zaak_id", flat=True))
        self.assertEqual(remaining, [zaak2.pk])
        self.assertFalse(ZaakObject.objects.filter(pk=obj1.pk).exists())

    def test_handle_destroy_deletes_objects(self):
        zaak = ZaakFactory()
        ZaakObject.objects.create(zaak=zaak, object=resource_url, object_type="overig")

        message = {
            "resource": "object",
            "actie": "destroy",
            "resourceUrl": resource_url,
            "kanaal": "objecten",
        }

        handlers.handle(message)
        self.assertEqual(ZaakObject.objects.count(), 0)
