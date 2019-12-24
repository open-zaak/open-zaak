"""
Test the custom admin view to manage autorisaties for an application.
"""

from urllib.parse import urlparse

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.test import TransactionTestCase, override_settings, tag
from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding

from openzaak.accounts.tests.factories import UserFactory
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.tests.utils import mock_nrc_oas_get
from openzaak.utils import build_absolute_url

from ...constants import RelatedTypeSelectionMethods
from ..factories import ApplicatieFactory, AutorisatieSpecFactory


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
class ManageAutorisatiesAdmin(TransactionTestCase):
    def setUp(self):
        super().setUp()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        user = UserFactory.create(is_staff=True)
        perm = Permission.objects.get_by_natural_key(
            "change_applicatie", "authorizations", "applicatie"
        )
        user.user_permissions.add(perm)
        self.applicatie = ApplicatieFactory.create()
        self.client.force_login(user)
        self.url = reverse(
            "admin:authorizations_applicatie_autorisaties",
            kwargs={"object_id": self.applicatie.pk},
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a ZaakType - this should trigger a new autorisatie being installed
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a ZaakType - this should trigger a new autorisatie being installed
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a informatieobjecttype - this should trigger a new autorisatie being installed
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a InformatieObjectType - this should trigger a new autorisatie
        # being installed
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())

        # create a besluittype - this should trigger a new autorisatie being installed
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 1)

        # create a InformatieObjectType - this should trigger a new autorisatie
        # being installed
        BesluitTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        # creating other types should not trigger anything, nor error
        ZaakTypeFactory.create()
        InformatieObjectTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(m.called)

    @override_settings(NOTIFICATIONS_DISABLED=False)
    @requests_mock.Mocker()
    def test_changes_send_notifications(self, m):
        mock_nrc_oas_get(m)
        m.post(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", status_code=201
        )
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(m.called)

    @override_settings(NOTIFICATIONS_DISABLED=False)
    @requests_mock.Mocker()
    def test_new_zt_all_current_and_future_send_notifications(self, m):
        mock_nrc_oas_get(m)
        m.post(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", status_code=201
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

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Autorisatie.objects.exists())
        self.assertFalse(m.called)

        # create a ZaakType - this should trigger a new autorisatie being installed
        ZaakTypeFactory.create()
        self.assertEqual(self.applicatie.autorisaties.count(), 1)
        self.assertTrue(m.called)
