# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test the custom admin view to manage autorisaties for an application.
"""

from unittest.mock import patch
from urllib.parse import urlparse

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings, tag
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

import requests_mock
from django_webtest import WebTest
from freezegun import freeze_time
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from zgw_consumers.test import generate_oas_component

from openzaak.accounts.tests.factories import UserFactory
from openzaak.components.catalogi.models.informatieobjecttype import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import mock_ztc_oas_get
from openzaak.utils import build_absolute_url

from ...constants import RelatedTypeSelectionMethods
from ...models import AutorisatieSpec
from ..factories import ApplicatieFactory, AutorisatieFactory, AutorisatieSpecFactory

ZTC_URL = "https://ztc.com/api/v1"
ZAAKTYPE1 = f"{ZTC_URL}/zaaktypen/1"
ZAAKTYPE2 = f"{ZTC_URL}/zaaktypen/2"
IOTYPE1 = f"{ZTC_URL}/informatieobjecttypen/1"
IOTYPE2 = f"{ZTC_URL}/informatieobjecttypen/2"
BESLUITTYPE1 = f"{ZTC_URL}/besluittypen/1"
BESLUITTYPE2 = f"{ZTC_URL}/besluittypen/2"


@tag("admin-autorisaties")
class PermissionTests(WebTest):
    """
    Test that the permission checks are implmeented correctly.
    """

    @classmethod
    def setUpTestData(cls):
        # non-priv user
        cls.user = UserFactory.create(is_staff=True)

        # priv user
        cls.privileged_user = UserFactory.create(is_staff=True)
        perm = Permission.objects.get_by_natural_key(
            "change_applicatie", "authorizations", "applicatie"
        )
        cls.privileged_user.user_permissions.add(perm)

        cls.applicatie = ApplicatieFactory.create()

    def test_non_privileged_user(self):
        url = reverse(
            "admin:authorizations_applicatie_autorisaties",
            kwargs={"object_id": self.applicatie.pk},
        )

        response = self.app.get(url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_privileged_user(self):
        url = reverse(
            "admin:authorizations_applicatie_autorisaties",
            kwargs={"object_id": self.applicatie.pk},
        )

        response = self.app.get(url, user=self.privileged_user)

        self.assertEqual(response.status_code, 200)


@tag("admin-autorisaties")
class ApplicatieInlinesAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        # priv user
        cls.user = UserFactory.create(is_staff=True)
        _perms = [
            ("change_applicatie", "authorizations", "applicatie"),
            ("view_autorisatie", "authorizations", "autorisatie"),
        ]
        perms = [Permission.objects.get_by_natural_key(*_perm) for _perm in _perms]
        cls.user.user_permissions.add(*perms)

        cls.applicatie = ApplicatieFactory.create()

        cls.url = reverse(
            "admin:authorizations_applicatie_change",
            kwargs={"object_id": cls.applicatie.id},
        )

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def _add_autorisatie(self, obj, **kwargs):
        url = build_absolute_url(obj.get_absolute_api_url())
        field = obj._meta.model_name
        Autorisatie.objects.create(
            applicatie=self.applicatie, **{field: url, **kwargs},
        )


@tag("admin-autorisaties")
@freeze_time("2022-01-01")
class ManageAutorisatiesAdmin(NotificationsConfigMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        cls.user = user = UserFactory.create(is_staff=True)
        perm = Permission.objects.get_by_natural_key(
            "change_applicatie", "authorizations", "applicatie"
        )
        user.user_permissions.add(perm)
        cls.applicatie = ApplicatieFactory.create()

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)
        self.url = reverse(
            "admin:authorizations_applicatie_autorisaties",
            kwargs={"object_id": self.applicatie.pk},
        )
        self.applicatie_url = reverse(
            "applicatie-detail", kwargs={"version": 1, "uuid": self.applicatie.uuid}
        )

    def test_page_returns_on_get(self):
        # set up some initial data
        iot = InformatieObjectTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            informatieobjecttype=build_absolute_url(iot.get_absolute_api_url()),
        )
        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
        )
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.nrc,
            scopes=["notificaties.consumeren"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_add_autorisatie_all_current_zaaktypen(self):
        zt1 = ZaakTypeFactory.create(concept=False)
        zt2 = ZaakTypeFactory.create(concept=True)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        urls = [
            reverse("zaaktype-detail", kwargs={"version": 1, "uuid": zt1.uuid}),
            reverse("zaaktype-detail", kwargs={"version": 1, "uuid": zt2.uuid}),
        ]

        for autorisatie in Autorisatie.objects.all():
            with self.subTest(autorisatie=autorisatie):
                self.assertEqual(autorisatie.component, ComponentTypes.zrc)
                self.assertEqual(autorisatie.scopes, ["zaken.lezen"])
                self.assertEqual(
                    autorisatie.max_vertrouwelijkheidaanduiding,
                    VertrouwelijkheidsAanduiding.beperkt_openbaar,
                )
                self.assertIsInstance(autorisatie.zaaktype, str)
                parsed = urlparse(autorisatie.zaaktype)
                self.assertEqual(parsed.scheme, "http")
                self.assertEqual(parsed.netloc, "testserver")
                self.assertIn(parsed.path, urls)

    def test_add_autorisatie_all_current_and_future_zaaktypen(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a ZaakType - this should trigger a new autorisatie being installed
        with self.captureOnCommitCallbacks(execute=True):
            ZaakTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

    def test_noop_all_current_and_future_zaaktypen(self):
        zt = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a ZaakType - this should trigger a new autorisatie being installed
        with self.captureOnCommitCallbacks(execute=True):
            ZaakTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

    def test_add_autorisatie_all_current_informatieobjecttypen(self):
        iot1 = InformatieObjectTypeFactory.create(concept=False)
        iot2 = InformatieObjectTypeFactory.create(concept=True)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["documenten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        urls = [
            reverse(
                "informatieobjecttype-detail", kwargs={"version": 1, "uuid": iot1.uuid}
            ),
            reverse(
                "informatieobjecttype-detail", kwargs={"version": 1, "uuid": iot2.uuid}
            ),
        ]

        for autorisatie in Autorisatie.objects.all():
            with self.subTest(autorisatie=autorisatie):
                self.assertEqual(autorisatie.component, ComponentTypes.drc)
                self.assertEqual(autorisatie.scopes, ["documenten.lezen"])
                self.assertEqual(
                    autorisatie.max_vertrouwelijkheidaanduiding,
                    VertrouwelijkheidsAanduiding.beperkt_openbaar,
                )
                self.assertIsInstance(autorisatie.informatieobjecttype, str)
                parsed = urlparse(autorisatie.informatieobjecttype)
                self.assertEqual(parsed.scheme, "http")
                self.assertEqual(parsed.netloc, "testserver")
                self.assertIn(parsed.path, urls)

    def test_add_autorisatie_all_current_and_future_informatieobjecttypen(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["documenten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a informatieobjecttype - this should trigger a new autorisatie being installed
        with self.captureOnCommitCallbacks(execute=True):
            InformatieObjectTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

    def test_noop_all_current_and_future_informatieobjecttypen(self):
        iot = InformatieObjectTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            informatieobjecttype=f"http://testserver{iot.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["documenten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a InformatieObjectType - this should trigger a new autorisatie
        # being installed
        with self.captureOnCommitCallbacks(execute=True):
            InformatieObjectTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

    def test_add_autorisatie_all_current_besluittypen(self):
        bt1 = BesluitTypeFactory.create(concept=False)
        bt2 = BesluitTypeFactory.create(concept=True)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        urls = [
            reverse("besluittype-detail", kwargs={"version": 1, "uuid": bt1.uuid}),
            reverse("besluittype-detail", kwargs={"version": 1, "uuid": bt2.uuid}),
        ]

        for autorisatie in Autorisatie.objects.all():
            with self.subTest(autorisatie=autorisatie):
                self.assertEqual(autorisatie.component, ComponentTypes.brc)
                self.assertEqual(autorisatie.scopes, ["besluiten.lezen"])
                self.assertEqual(autorisatie.max_vertrouwelijkheidaanduiding, "")
                self.assertIsInstance(autorisatie.besluittype, str)
                parsed = urlparse(autorisatie.besluittype)
                self.assertEqual(parsed.scheme, "http")
                self.assertEqual(parsed.netloc, "testserver")
                self.assertIn(parsed.path, urls)

    def test_add_autorisatie_all_current_and_future_besluittypen(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a besluittype - this should trigger a new autorisatie being installed
        with self.captureOnCommitCallbacks(execute=True):
            BesluitTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

    def test_noop_all_current_and_future_besluittypen(self):
        bt = BesluitTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
            informatieobjecttype=f"http://testserver{bt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a InformatieObjectType - this should trigger a new autorisatie
        # being installed
        with self.captureOnCommitCallbacks(execute=True):
            BesluitTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        # creating other types should not trigger anything, nor error
        with self.captureOnCommitCallbacks(execute=True):
            ZaakTypeFactory.create()
            InformatieObjectTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

    @override_settings(NOTIFICATIONS_DISABLED=False)
    @requests_mock.Mocker()
    def test_no_changes_no_notifications(self, m):
        zt = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zt.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(m.called)

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_changes_send_notifications(self, mock_notif):
        zt = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen", "zaken.bijwerken"],  # modified
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zt.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)

        mock_notif.assert_called_with(
            {
                "kanaal": "autorisaties",
                "hoofdObject": f"http://testserver{self.applicatie_url}",
                "resource": "applicatie",
                "resourceUrl": f"http://testserver{self.applicatie_url}",
                "actie": "update",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "kenmerken": {},
            }
        )

    @override_settings(
        NOTIFICATIONS_DISABLED=False,
        OPENZAAK_DOMAIN="openzaak.example.com",
        OPENZAAK_REWRITE_HOST=True,
        ALLOWED_HOSTS=["testserver", "openzaak.example.com"],
    )
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_changes_send_notifications_with_openzaak_domain_setting(self, mock_notif):
        zt = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen", "zaken.bijwerken"],  # modified
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zt.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)

        mock_notif.assert_called_with(
            {
                "kanaal": "autorisaties",
                "hoofdObject": f"http://openzaak.example.com{self.applicatie_url}",
                "resource": "applicatie",
                "resourceUrl": f"http://openzaak.example.com{self.applicatie_url}",
                "actie": "update",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "kenmerken": {},
            }
        )

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_new_zt_all_current_and_future_send_notifications(self, mock_notif):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a ZaakType - this should trigger a new autorisatie being installed
        with self.captureOnCommitCallbacks(execute=True):
            with self.captureOnCommitCallbacks(execute=True):
                ZaakTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        mock_notif.assert_called_with(
            {
                "kanaal": "autorisaties",
                "hoofdObject": f"http://testserver{self.applicatie_url}",
                "resource": "applicatie",
                "resourceUrl": f"http://testserver{self.applicatie_url}",
                "actie": "update",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "kenmerken": {},
            }
        )

        with self.subTest("OPENZAAK_DOMAIN setting"):
            with override_settings(
                OPENZAAK_DOMAIN="openzaak.example.com",
                ALLOWED_HOSTS=["openzaak.example.com", "testserver"],
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    with self.captureOnCommitCallbacks(execute=True):
                        ZaakTypeFactory.create()

                mock_notif.assert_called_with(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://openzaak.example.com{self.applicatie_url}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://openzaak.example.com{self.applicatie_url}",
                        "actie": "update",
                        "aanmaakdatum": "2022-01-01T00:00:00Z",
                        "kenmerken": {},
                    }
                )

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False, IS_HTTPS=True)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_notification_body_current_and_future(self, mock_notif):
        applicatie = ApplicatieFactory.create()
        AutorisatieSpecFactory.create(
            applicatie=applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        with self.captureOnCommitCallbacks(execute=True):
            with self.captureOnCommitCallbacks(execute=True):
                InformatieObjectTypeFactory.create()

        path = reverse(
            "applicatie-detail", kwargs={"version": 1, "uuid": applicatie.uuid}
        )
        mock_notif.assert_called_with(
            {
                "kanaal": "autorisaties",
                "hoofdObject": f"https://testserver{path}",
                "resource": "applicatie",
                "resourceUrl": f"https://testserver{path}",
                "actie": "update",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "kenmerken": {},
            }
        )

    @requests_mock.Mocker()
    def test_add_autorisatie_external_zaaktypen(self, m):
        mock_ztc_oas_get(m)
        zt1 = generate_oas_component("ztc", "schemas/ZaakType", url=ZAAKTYPE1)
        zt2 = generate_oas_component("ztc", "schemas/ZaakType", url=ZAAKTYPE2)
        m.get(ZAAKTYPE1, json=zt1)
        m.get(ZAAKTYPE2, json=zt2)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-0-externe_typen": [ZAAKTYPE1, ZAAKTYPE2],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)

        autorisatie1, autorisatie2 = Autorisatie.objects.all()

        self.assertEqual(autorisatie1.zaaktype, ZAAKTYPE1)
        self.assertEqual(autorisatie2.zaaktype, ZAAKTYPE2)

    @requests_mock.Mocker()
    def test_add_autorisatie_external_iotypen(self, m):
        mock_ztc_oas_get(m)
        iot1 = generate_oas_component(
            "ztc", "schemas/InformatieObjectType", url=IOTYPE1
        )
        iot2 = generate_oas_component(
            "ztc", "schemas/InformatieObjectType", url=IOTYPE2
        )
        m.get(IOTYPE1, json=iot1)
        m.get(IOTYPE2, json=iot2)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["documenten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-0-externe_typen": [IOTYPE1, IOTYPE2],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)

        autorisatie1, autorisatie2 = Autorisatie.objects.all()

        self.assertEqual(autorisatie1.informatieobjecttype, IOTYPE1)
        self.assertEqual(autorisatie2.informatieobjecttype, IOTYPE2)

    @requests_mock.Mocker()
    def test_add_autorisatie_external_besluittypen(self, m):
        mock_ztc_oas_get(m)
        bt1 = generate_oas_component("ztc", "schemas/BesluitType", url=BESLUITTYPE1)
        bt2 = generate_oas_component("ztc", "schemas/BesluitType", url=BESLUITTYPE2)
        m.get(BESLUITTYPE1, json=bt1)
        m.get(BESLUITTYPE2, json=bt2)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-externe_typen": [BESLUITTYPE1, BESLUITTYPE2],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 2)

        autorisatie1, autorisatie2 = Autorisatie.objects.all()

        self.assertEqual(autorisatie1.besluittype, BESLUITTYPE1)
        self.assertEqual(autorisatie2.besluittype, BESLUITTYPE2)

    def test_add_autorisatie_external_zaaktype_invalid_url(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-0-externe_typen": ["badurl"],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=False)
    def test_add_autorisatie_external_zaaktype_invalid_resource(self, *mocks):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-0-externe_typen": ["https://example.com"],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)

    def test_add_authorizatie_without_types(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.ztc,
            "form-0-scopes": ["catalogi.lezen"],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        autorisatie = self.applicatie.autorisaties.get()
        self.assertEqual(autorisatie.component, ComponentTypes.ztc)
        self.assertEqual(autorisatie.scopes, ["catalogi.lezen"])

    def test_add_autorisatie_zaaktypen_overlap(self):
        zt1 = ZaakTypeFactory.create()
        ZaakTypeFactory.create()

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": ["zaken.aanmaken", "zaken.lezen"],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-1-zaaktypen": [zt1.id],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)
        self.assertEqual(
            response.context_data["formset"]._non_form_errors[0],
            _("{field} may not have overlapping scopes.").format(field="zaaktypen"),
        )

    def test_add_autorisatie_overlap_without_types(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.ztc,
            "form-0-scopes": ["catalogi.lezen", "catalogi.schrijven"],
            "form-1-component": ComponentTypes.ztc,
            "form-1-scopes": ["catalogi.lezen"],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)
        self.assertEqual(
            response.context_data["formset"]._non_form_errors[0],
            _("Scopes in {component} may not be duplicated.").format(component="ztc"),
        )

    @tag("gh-1080")
    def test_autorisaties_visible_even_if_only_a_spec_exists_brc(self):
        """
        Assert that the initial form data contains autorisatiespecs if only the spec exists.

        Regression test for Github issue #1080.
        """
        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        initial_data = response.context["formdata"]
        self.assertEqual(len(initial_data), 2)  # 1 form, 1 empty form
        form_data = initial_data[0]
        self.assertEqual(form_data["values"]["component"], ComponentTypes.brc)
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(form_data["values"]["scopes"], ["besluiten.lezen"])

    def test_autorisaties_visible_even_if_only_a_spec_exists_zrc(self):
        """
        Assert that the initial form data contains autorisatiespecs if only the spec exists.

        Regression test for Github issue #978.
        """
        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        initial_data = response.context["formdata"]
        self.assertEqual(len(initial_data), 2)  # 1 form, 1 empty form
        form_data = initial_data[0]

        self.assertEqual(form_data["values"]["component"], ComponentTypes.zrc)
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(form_data["values"]["scopes"], ["zaken.lezen"])

    def test_autorisaties_visible_even_if_only_a_spec_exists_drc(self):
        """
        Assert that the initial form data contains autorisatiespecs if only the spec exists.

        Regression test for Github issue #978.
        """
        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        initial_data = response.context["formdata"]
        self.assertEqual(len(initial_data), 2)  # 1 form, 1 empty form
        form_data = initial_data[0]

        self.assertEqual(form_data["values"]["component"], ComponentTypes.drc)
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(form_data["values"]["scopes"], ["documenten.lezen"])

    @tag("gh-1081")
    def test_remove_iotype_with_autorisaties_linked(self):
        """
        Assert that the autorisatie is deleted if the related informatieobjecttype is deleted.

        Regression test for Github issue #1081.

        Note that there is a similar test in
        openzaak.components.catalogi.tests.test_zaaktype.ZaaktypeDeleteAutorisatieTests
        """
        # set up unrelated other authorization spec
        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
        )

        # set up reproduction case
        iotype = InformatieObjectTypeFactory.create(concept=True)
        url = f"http://testserver{iotype.get_absolute_api_url()}"
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            informatieobjecttype=url,
        )

        # now delete the iotype - which is allowed since it's a draft
        InformatieObjectType.objects.filter(id=iotype.id).delete()

        # check that the admin page does not crash
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        initial_data = response.context["formdata"]
        self.assertEqual(len(initial_data), 2)  # 1 empty form, 1 unrelated auth spec

    @tag("gh-1584")
    def test_related_object_does_not_exist(self):
        """
        Assert that the autorisaties view does not crash
        if an autorisatie fails to delete after its related object is deleted.
        """

        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            informatieobjecttype="http://testserver/url_to_nowhere/00000000-0000-0000-0000-000000000000",
        )

        # check that the admin page does not crash
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @tag("gh-1626")
    def test_autorisatie_spec_is_removed_when_all_and_future_unselected_besluittype(
        self,
    ):

        BesluitTypeFactory.create(concept=False)

        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(AutorisatieSpec.objects.count(), 1)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(AutorisatieSpec.objects.count(), 0)

        response = self.client.get(self.url)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current,
        )

    @tag("gh-1626")
    def test_autorisatie_spec_is_removed_when_all_and_future_unselected_zaaktype(self):

        ZaakTypeFactory.create(concept=False)

        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(AutorisatieSpec.objects.count(), 1)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AutorisatieSpec.objects.count(), 0)

        response = self.client.get(self.url)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current,
        )

    @tag("gh-1626")
    def test_autorisatie_spec_is_removed_when_all_and_future_unselected_documenten(
        self,
    ):

        iot = InformatieObjectTypeFactory.create(concept=False)
        InformatieObjectTypeFactory.create(concept=False)

        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=["documenten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(AutorisatieSpec.objects.count(), 1)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["documenten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-informatieobjecttypen": [iot.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AutorisatieSpec.objects.count(), 0)

        response = self.client.get(self.url)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.manual_select,
        )

    @tag("gh-1626")
    def test_autorisatie_spec_is_not_shared_within_component(self):

        BesluitTypeFactory.create(concept=False)

        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        AutorisatieSpecFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=["besluiten.bijwerken"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        form_data = response.context["formdata"][0]
        self.assertEqual(
            form_data["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
        self.assertEqual(AutorisatieSpec.objects.count(), 2)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": ["besluiten.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.all_current,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-1-component": ComponentTypes.brc,
            "form-1-scopes": ["besluiten.bijwerken"],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.all_current_and_future,
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(AutorisatieSpec.objects.count(), 1)

        response = self.client.get(self.url)

        form_data_1 = response.context["formdata"][0]
        form_data_2 = response.context["formdata"][1]
        self.assertEqual(
            form_data_1["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current,
        )
        self.assertEqual(
            form_data_2["values"]["related_type_selection"],
            RelatedTypeSelectionMethods.all_current_and_future,
        )
