# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.models import BesluitType
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    ZaakTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import ClearCachesMixin
from openzaak.tests.utils.admin import AdminTestMixin


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

    def test_besluittype_notify_on_create(self, mock_notif):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )

        url = reverse("admin:catalogi_besluittype_add")

        response = self.app.get(url)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
        )

        form = response.forms["besluittype_form"]
        form["datum_begin_geldigheid"] = "2019-01-01"
        form["zaaktypen"] = zaaktype.id
        form["catalogus"] = self.catalogus.pk

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        besluittype = BesluitType.objects.get()
        besluittype_url = reverse(
            "zaken:besluittype-detail",
            kwargs={"uuid": besluittype.uuid, "version": 1},
        )
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{besluittype_url}",
                "kanaal": "besluittypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "create",
                "resource": "besluittype",
                "resourceUrl": f"http://testserver{besluittype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            },
            None,
        )

    def test_besluit_notify_on_change(self, mock_notif):
        besluittype = BesluitTypeFactory.create(
            concept=True, omschrijving="test", catalogus=self.catalogus
        )
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        response = self.app.get(url)
        form = response.forms["besluittype_form"]
        form["omschrijving"] = "different-test"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        besluittype_url = reverse(
            "zaken:besluittype-detail",
            kwargs={"uuid": besluittype.uuid, "version": 1},
        )
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{besluittype_url}",
                "kanaal": "besluittypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "update",
                "resource": "besluittype",
                "resourceUrl": f"http://testserver{besluittype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            },
            None,
        )

    def test_besluit_no_notify_on_no_change(self, mock_notif):
        besluit = BesluitTypeFactory.create(concept=True, omschrijving="test")
        url = reverse("admin:catalogi_besluittype_change", args=(besluit.pk,))

        response = self.app.get(url)
        form = response.forms["besluittype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        mock_notif.assert_not_called()
