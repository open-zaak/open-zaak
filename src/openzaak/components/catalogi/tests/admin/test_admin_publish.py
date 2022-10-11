# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest
from notifications_api_common.tests.utils import mock_notify

from openzaak.accounts.tests.factories import SuperUserFactory, UserFactory
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import (
    mock_resource_get,
    mock_resource_list,
    mock_selectielijst_oas_get,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import ClearCachesMixin, mock_nrc_oas_get

from ..factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


@requests_mock.Mocker()
class ZaaktypeAdminTests(
    NotificationsConfigMixin, ReferentieLijstServiceMixin, ClearCachesMixin, WebTest
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.allowed_years = [2017, 2020]
        config.save()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch(
        "notifications_api_common.viewsets.NotificationViewSetMixin.send_notification.delay",
        side_effect=mock_notify,
    )
    def test_publish_zaaktype(self, m, mock_notif):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        mock_nrc_oas_get(m)
        m.post(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", status_code=201
        )

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            verlenging_mogelijk=False,
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

        # Verify notification is sent
        notif_request = m.last_request
        self.assertEqual(notif_request.method, "POST")
        self.assertEqual(
            notif_request.url, "https://notificaties-api.vng.cloud/api/v1/notificaties"
        )
        notification = notif_request.json()
        self.assertEqual(notification["actie"], "update")

    def test_publish_besluittype(self, m):
        besluittype = BesluitTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["besluittype_form"]

        response = form.submit("_publish").follow()

        besluittype.refresh_from_db()
        self.assertFalse(besluittype.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

    def test_publish_informatieobjecttype(self, m):
        iot = InformatieObjectTypeFactory.create(
            concept=True, vertrouwelijkheidaanduiding="openbaar"
        )
        iot.zaaktypeinformatieobjecttype_set.all().delete()
        url = reverse("admin:catalogi_informatieobjecttype_change", args=(iot.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["informatieobjecttype_form"]

        response = form.submit("_publish").follow()

        iot.refresh_from_db()
        self.assertFalse(iot.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

    def test_publish_zaaktype_related_to_concept_besluittype_fails(self, m):
        mock_selectielijst_oas_get(m)
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            verlenging_mogelijk=False,
        )
        BesluitTypeFactory.create(concept=True, zaaktypen=[zaaktype])
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

        # Check that the error is shown on the page
        error_message = response.html.find("li", {"class": "error"})
        self.assertIn(
            _("All related resources should be published"), error_message.text
        )

        # Verify that the publish button is still visible and enabled.
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

    def test_publish_zaaktype_related_to_concept_informatieobjecttype_fails(self, m):
        mock_selectielijst_oas_get(m)
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            verlenging_mogelijk=False,
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=True, zaaktype=zaaktype
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

        # Check that the error is shown on the page
        error_message = response.html.find("li", {"class": "error"})
        self.assertIn(
            _("All related resources should be published"), error_message.text
        )

        # Verify that the publish button is still visible and enabled.
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)


@tag("readonly-user")
class ReadOnlyUserTests(ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user = UserFactory.create(is_staff=True)
        view_zaaktype = Permission.objects.get(codename="view_zaaktype")
        view_informatieobjecttype = Permission.objects.get(
            codename="view_informatieobjecttype"
        )
        view_besluittype = Permission.objects.get(codename="view_besluittype")
        user.user_permissions.add(
            view_zaaktype, view_informatieobjecttype, view_besluittype
        )

        cls.user = user

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_zaaktype_publish_not_possible(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)

    def test_informatieobjecttype_publish_not_possible(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)

    def test_besluittype_publish_not_possible(self):
        besluittype = BesluitTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)
