# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import Mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from openzaak.components.catalogi.tests.factories import StatusTypeFactory
from openzaak.components.zaken.admin import StatusAdmin, ZaakAdmin

from ...api.cloud_events import ZAAK_GEMUTEERD, ZAAK_GEOPEND, ZAAK_VERWIJDEREN
from ...models import Zaak
from ..factories import StatusFactory, ZaakFactory
from ..test_cloud_events import CloudEventSettingMixin, patch_send_cloud_event


class ZaakAdminCloudEventTests(CloudEventSettingMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@test.com", password="pass"
        )

        self.site = AdminSite()
        self.admin = ZaakAdmin(Zaak, self.site)
        self.factory = RequestFactory()

        self.zaak = ZaakFactory.create()

    def test_admin_delete_zaak_triggers_cloud_event(self):
        request = self.factory.get("/")
        request.user = self.user
        with patch_send_cloud_event() as mock_send:
            self.admin.delete_model(request=request, obj=self.zaak)
            self.assert_cloud_event_sent(ZAAK_VERWIJDEREN, self.zaak, mock_send)

    def test_admin_update_laatst_geopend_triggers_cloud_event(self):
        self.zaak.laatst_geopend = timezone.now()
        request = self.factory.post("/")
        request.user = self.user
        with patch_send_cloud_event() as mock_send:
            self.admin.save_model(
                request=request, obj=self.zaak, form=Mock(), change=True
            )
            self.assert_cloud_event_sent(ZAAK_GEOPEND, self.zaak, mock_send)

    def test_admin_add_status_triggers_zaak_gemuteerd(self):
        statustype = StatusTypeFactory.create(zaaktype=self.zaak.zaaktype)
        status = StatusFactory.build(zaak=self.zaak, statustype=statustype)

        request = self.factory.post("/")
        request.user = self.user

        admin = StatusAdmin(status._meta.model, AdminSite())
        with patch_send_cloud_event() as mock_send:
            admin.save_model(request=request, obj=status, form=Mock(), change=False)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)
