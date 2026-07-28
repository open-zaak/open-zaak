# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag
from django.urls import reverse as django_reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.models import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    InformatieObjectTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import ClearCachesMixin
from openzaak.tests.utils.admin import AdminTestMixin
from openzaak.utils.urls import reverse


@tag("notifications")
@disable_admin_mfa()
@override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
@freeze_time("2022-01-01")
@patch("notifications_api_common.viewsets.send_notification.delay")
class NotificationAdminTests(
    NotificationsConfigMixin,
    ReferentieLijstServiceMixin,
    ClearCachesMixin,
    AdminTestMixin,
    WebTest,
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.allowed_years = [2017, 2020]
        config.save()

        cls.catalogus = CatalogusFactory.create()
        cls.catalogus_url = reverse(
            "catalogi:catalogus-detail",
            kwargs={"uuid": cls.catalogus.uuid, "version": 1},
        )

    def test_informatieobjecttype_notify_on_create(self, mock_notif):
        url = django_reverse("admin:catalogi_informatieobjecttype_add")

        response = self.app.get(url)

        form = response.forms["informatieobjecttype_form"]
        form["omschrijving"] = "different-test"
        form["datum_begin_geldigheid"] = "2019-01-01"
        form["catalogus"] = self.catalogus.pk
        form["vertrouwelijkheidaanduiding"].select("openbaar")
        form["informatieobjectcategorie"] = "main"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        iotype = InformatieObjectType.objects.get()
        iotype_url = reverse(iotype, namespace="documenten")
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{iotype_url}",
                "kanaal": "informatieobjecttypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "create",
                "resource": "informatieobjecttype",
                "resourceUrl": f"http://testserver{iotype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            },
            None,
        )

    def test_informatieobjecttype_notify_on_change(self, mock_notif):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True,
            omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            catalogus=self.catalogus,
        )
        url = django_reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]
        form["omschrijving"] = "different-test"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        iotype = InformatieObjectType.objects.get()
        iotype_url = reverse(iotype, namespace="documenten")
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{iotype_url}",
                "kanaal": "informatieobjecttypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "update",
                "resource": "informatieobjecttype",
                "resourceUrl": f"http://testserver{iotype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            },
            None,
        )

    def test_no_informatieobjecttype_notify_on_no_change(self, mock_notif):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True, omschrijving="test", vertrouwelijkheidaanduiding="openbaar"
        )
        url = django_reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        mock_notif.assert_not_called()
