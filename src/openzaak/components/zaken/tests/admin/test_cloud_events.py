# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase, override_settings

from vng_api_common.tests import reverse

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
)
from openzaak.components.zaken.admin import StatusAdmin, ZaakAdmin

from ...api.cloudevents import ZAAK_GEMUTEERD, ZAAK_VERWIJDEREN
from ...models import Zaak
from ..factories import StatusFactory, ZaakFactory
from ..test_cloud_events import (
    CloudEventSettingMixin,
)


@patch("notifications_api_common.tasks.send_cloudevent.delay")
@patch(
    "notifications_api_common.cloudevents.uuid.uuid4",
    lambda: "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
)
@override_settings(NOTIFICATIONS_SOURCE="oz-test")
class ZaakAdminCloudEventTests(CloudEventSettingMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = SuperUserFactory.create()

        self.site = AdminSite()
        self.admin = ZaakAdmin(Zaak, self.site)
        self.factory = RequestFactory()

        self.zaak = ZaakFactory.create()

    def test_admin_delete_zaak_triggers_cloud_event(self, mock_send_cloudevent):
        request = self.factory.get("/")
        request.user = self.user

        self.admin.delete_model(request=request, obj=self.zaak)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_VERWIJDEREN,
                "subject": str(self.zaak.uuid),
                "time": "2025-09-23T12:00:00Z",
                "dataref": reverse(self.zaak),
                "datacontenttype": "application/json",
                "data": {},
            }
        )

    def test_admin_add_status_triggers_zaak_gemuteerd(self, mock_send_cloudevent):
        statustype = StatusTypeFactory.create(zaaktype=self.zaak.zaaktype)
        status = StatusFactory.build(zaak=self.zaak, statustype=statustype)

        request = self.factory.post("/")
        request.user = self.user

        admin = StatusAdmin(status._meta.model, AdminSite())
        with self.subTest("Status change False"):
            admin.save_model(request=request, obj=status, form=Mock(), change=False)

            self.assertEqual(mock_send_cloudevent.call_count, 1)

            mock_send_cloudevent.assert_called_once_with(
                {
                    "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                    "source": settings.NOTIFICATIONS_SOURCE,
                    "specversion": settings.CLOUDEVENT_SPECVERSION,
                    "type": ZAAK_GEMUTEERD,
                    "subject": str(self.zaak.uuid),
                    "time": "2025-09-23T12:00:00Z",
                    "dataref": reverse(self.zaak),
                    "datacontenttype": "application/json",
                    "data": {},
                }
            )

        mock_send_cloudevent.reset_mock()

        with self.subTest("Status change True"):
            admin.save_model(request=request, obj=status, form=Mock(), change=True)
            self.assertEqual(mock_send_cloudevent.call_count, 0)
