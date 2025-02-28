# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test the custom admin view to manage autorisaties for an application.
"""

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings, tag
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse as _reverse
from zgw_consumers.test import generate_oas_component

from openzaak.accounts.tests.factories import UserFactory
from openzaak.components.autorisaties.api.scopes import SCOPE_AUTORISATIES_BIJWERKEN
from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
)
from openzaak.components.catalogi.models.informatieobjecttype import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import mock_ztc_oas_get
from openzaak.utils import build_absolute_url

from ...constants import RelatedTypeSelectionMethods
from ...models import CatalogusAutorisatie
from ..factories import (
    ApplicatieFactory,
    AutorisatieFactory,
    CatalogusAutorisatieFactory,
)

ZTC_URL = "https://ztc.com/api/v1"
ZAAKTYPE1 = f"{ZTC_URL}/zaaktypen/1"
ZAAKTYPE2 = f"{ZTC_URL}/zaaktypen/2"
IOTYPE1 = f"{ZTC_URL}/informatieobjecttypen/1"
IOTYPE2 = f"{ZTC_URL}/informatieobjecttypen/2"
BESLUITTYPE1 = f"{ZTC_URL}/besluittypen/1"
BESLUITTYPE2 = f"{ZTC_URL}/besluittypen/2"


@tag("admin-autorisaties")
@disable_admin_mfa()
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
@disable_admin_mfa()
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
            applicatie=self.applicatie,
            **{field: url, **kwargs},
        )


@tag("admin-autorisaties")
@freeze_time("2022-01-01")
@disable_admin_mfa()
class ManageAutorisatiesAdmin(NotificationsConfigMixin, TestCase):
    maxDiff = None

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

        cls.url = reverse(
            "admin:authorizations_applicatie_autorisaties",
            kwargs={"object_id": cls.applicatie.pk},
        )
        cls.applicatie_url = reverse(
            "applicatie-detail", kwargs={"version": 1, "uuid": cls.applicatie.uuid}
        )
        cls.catalogus = CatalogusFactory.create()

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

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
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.nrc,
            scopes=["notificaties.consumeren"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_no_changes_no_notifications(self, mock_send_notif):
        """
        Verify that saving the form without any changes does not result in notifications
        """
        zt = ZaakTypeFactory.create()
        zt2 = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.aanmaken"],
            catalogus=zt2.catalogus,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zt.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": ["zaken.aanmaken"],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [zt2.catalogus.id],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(mock_send_notif.called)

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_changes_to_regular_autorisatie_send_notifications(self, mock_notif):
        zt = ZaakTypeFactory.create()
        zt2 = ZaakTypeFactory.create()
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{zt.get_absolute_api_url()}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.aanmaken"],
            catalogus=zt2.catalogus,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen", "zaken.bijwerken"],  # modified
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zt.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": ["zaken.aanmaken"],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [zt2.catalogus.id],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,  # modified
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

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_changes_to_catalogus_autorisatie_send_notifications(self, mock_notif):
        zt = ZaakTypeFactory.create()
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.aanmaken"],
            catalogus=zt.catalogus,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.aanmaken"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [zt.catalogus.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,  # modified
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

    @patch("vng_api_common.oas.fetcher")
    @patch("openzaak.utils.validators.obj_has_shape", return_value=False)
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
            "form-0-externe_typen": ["https://external.catalogi.com/api/v1/1234"],
        }

        with requests_mock.Mocker() as m:
            m.get(
                "https://external.catalogi.com/api/v1/1234", json={"invalid": "shape"}
            )
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)

        expected_errors = {
            "externe_typen": [
                {
                    "msg": _(
                        "De URL {url} resource lijkt niet op een `ZaakType`. Geef een geldige URL op."
                    ).format(url="https://external.catalogi.com/api/v1/1234"),
                    "code": "invalid-resource",
                }
            ]
        }
        self.assertEqual(response.context["formdata"][0]["errors"], expected_errors)

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
        zt = ZaakTypeFactory.create()

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": ["zaken.lezen"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
            "form-0-catalogi": [zt.catalogus.pk],
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": ["zaken.aanmaken", "zaken.lezen"],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-1-zaaktypen": [zt.id],
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

    @tag("gh-1594")
    def test_add_autorisaties_without_scopes(self):
        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.ztc,
            "form-0-scopes": [],
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": [],
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Autorisatie.objects.count(), 0)
        self.assertEqual(
            response.context_data["formset"]._non_form_errors[0],
            _("One or more authorizations are missing scopes."),
        )
        self.assertEqual(
            response.context_data["formset"][0].errors["scopes"],
            [_("This field is required.")],
        )
        self.assertEqual(
            response.context_data["formset"][1].errors["scopes"],
            [_("This field is required.")],
        )

    @tag("gh-1081")
    def test_remove_iotype_with_autorisaties_linked(self):
        """
        Assert that the autorisatie is deleted if the related informatieobjecttype is deleted.

        Regression test for Github issue #1081.

        Note that there is a similar test in
        openzaak.components.catalogi.tests.test_zaaktype.ZaaktypeDeleteAutorisatieTests
        """
        # create unrelated CatalogusAutorisatie
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
            catalogus=self.catalogus,
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
        self.assertEqual(
            len(initial_data), 2
        )  # 1 empty form, 1 unrelated catalogusautorisatie

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

    @tag("gh-1584")
    @override_settings(
        ALLOWED_HOSTS=["testserver", "differenttestserver"],
    )
    def test_autorisatie_added_on_different_domain_is_deleted(self):
        """
        Tests that an autorisatie is saved in a way that the sync_autorisaties catalogi signal can delete
        """

        zaaktype = ZaakTypeFactory.create()

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
            "form-0-zaaktypen": [zaaktype.pk],
        }

        response = self.client.post(self.url, data, SERVER_NAME="differenttestserver")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Autorisatie.objects.count(), 1)

        autorisatie = Autorisatie.objects.get()
        # domain expected by sync_autorisaties signal
        self.assertEqual(
            autorisatie.zaaktype, "http://testserver" + zaaktype.get_absolute_api_url()
        )

        zaaktype.delete()

        with self.assertRaises(Autorisatie.DoesNotExist):
            autorisatie.refresh_from_db()
        self.assertEqual(Autorisatie.objects.count(), 0)
        # Because the last Autorisatie was deleted, the Applicatie itself is deleted as well
        self.assertEqual(Applicatie.objects.count(), 0)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_load_initial_data_external_types(self):
        """
        Test that external types for ZRC/BRC/DRC load properly, even if there are no local
        types linked to Autorisaties
        """
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            zaaktype="http://ztc.com/1234",
            scopes=[str(SCOPE_ZAKEN_BIJWERKEN)],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            informatieobjecttype="http://ztc.com/5678",
            scopes=[str(SCOPE_DOCUMENTEN_ALLES_LEZEN)],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            besluittype="http://ztc.com/4321",
            scopes=[str(SCOPE_BESLUITEN_AANMAKEN)],
        )

        response = self.client.get(self.url)

        # Regular Autorisatie with different scopes should be displayed separately
        expected_initial = [
            {
                "component": ComponentTypes.zrc,
                "scopes": [str(SCOPE_ZAKEN_BIJWERKEN)],
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "zaaktypen": set(),
                "externe_typen": ["http://ztc.com/1234"],
            },
            {
                "component": ComponentTypes.drc,
                "scopes": [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)],
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "informatieobjecttypen": set(),
                "externe_typen": ["http://ztc.com/5678"],
            },
            {
                "component": ComponentTypes.brc,
                "scopes": [str(SCOPE_BESLUITEN_AANMAKEN)],
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "besluittypen": set(),
                "externe_typen": ["http://ztc.com/4321"],
            },
        ]

        self.assertEqual(response.context["formset"].initial, expected_initial)

    @tag("gh-1661")
    def test_create_catalogus_autorisatie_for_zaken_api(self):
        """
        Assert that it is possible to create a CatalogusAutorisatie for Zaken API
        """
        scopes = [str(SCOPE_ZAKEN_ALLES_LEZEN), str(SCOPE_ZAKEN_CREATE)]
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk, zaaktype.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Autorisatie.objects.count(), 0)

        catalogus_autorisatie1, catalogus_autorisatie2 = (
            CatalogusAutorisatie.objects.order_by("catalogus")
        )

        self.assertEqual(catalogus_autorisatie1.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie1.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie1.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie1.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        self.assertEqual(catalogus_autorisatie2.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie2.catalogus, zaaktype.catalogus)
        self.assertEqual(catalogus_autorisatie2.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie2.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

    @tag("gh-1661")
    def test_create_catalogus_autorisatie_for_documenten_api(self):
        """
        Assert that it is possible to create a CatalogusAutorisatie for Documenten API
        """
        scopes = [str(SCOPE_DOCUMENTEN_ALLES_LEZEN), str(SCOPE_DOCUMENTEN_AANMAKEN)]
        iotype = InformatieObjectTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk, iotype.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Autorisatie.objects.count(), 0)

        catalogus_autorisatie1, catalogus_autorisatie2 = (
            CatalogusAutorisatie.objects.order_by("catalogus")
        )

        self.assertEqual(catalogus_autorisatie1.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie1.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie1.component, ComponentTypes.drc)
        self.assertEqual(catalogus_autorisatie1.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        self.assertEqual(catalogus_autorisatie2.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie2.catalogus, iotype.catalogus)
        self.assertEqual(catalogus_autorisatie2.component, ComponentTypes.drc)
        self.assertEqual(catalogus_autorisatie2.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

    @tag("gh-1661")
    def test_create_catalogus_autorisatie_for_besluiten_api(self):
        """
        Assert that it is possible to create a CatalogusAutorisatie for Besluiten API
        """
        scopes = [str(SCOPE_BESLUITEN_AANMAKEN), str(SCOPE_BESLUITEN_ALLES_LEZEN)]
        besluittype = BesluitTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.brc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk, besluittype.catalogus.pk],
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Autorisatie.objects.count(), 0)

        catalogus_autorisatie1, catalogus_autorisatie2 = (
            CatalogusAutorisatie.objects.order_by("catalogus")
        )

        self.assertEqual(catalogus_autorisatie1.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie1.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie1.component, ComponentTypes.brc)
        self.assertEqual(catalogus_autorisatie1.scopes, scopes)
        self.assertEqual(catalogus_autorisatie1.max_vertrouwelijkheidaanduiding, "")

        self.assertEqual(catalogus_autorisatie2.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie2.catalogus, besluittype.catalogus)
        self.assertEqual(catalogus_autorisatie2.component, ComponentTypes.brc)
        self.assertEqual(catalogus_autorisatie2.scopes, scopes)
        self.assertEqual(catalogus_autorisatie2.max_vertrouwelijkheidaanduiding, "")

    @tag("gh-1661")
    def test_load_initial_data_and_update_catalogus_autorisaties(self):
        """
        Test that it is possible to load existing CatalogusAutorisaties (along with
        regular Autorisaties) and update them
        """
        scopes = [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)]
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            catalogus=self.catalogus,
            scopes=scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeFactory.create(concept=False)
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            zaaktype=f"http://testserver/{_reverse(zaaktype)}",
            scopes=[str(SCOPE_ZAKEN_BIJWERKEN)],  # different scopes
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        response = self.client.get(self.url)

        # Regular Autorisatie with different scopes should be displayed separately
        expected_initial = [
            {
                "component": ComponentTypes.zrc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                "catalogi": [self.catalogus.pk],
            },
            {
                "component": ComponentTypes.zrc,
                "scopes": [str(SCOPE_ZAKEN_BIJWERKEN)],
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "zaaktypen": {zaaktype.pk},
                "externe_typen": [],
            },
        ]
        self.assertEqual(response.context["formset"].initial, expected_initial)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk, zaaktype.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        catalogus_autorisatie1, catalogus_autorisatie2 = (
            CatalogusAutorisatie.objects.order_by("catalogus")
        )

        self.assertEqual(catalogus_autorisatie1.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie1.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie1.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie1.scopes, scopes)
        # Max VA was changed
        self.assertEqual(
            catalogus_autorisatie1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        # New CatalogusAutorisatie was created
        self.assertEqual(catalogus_autorisatie2.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie2.catalogus, zaaktype.catalogus)
        self.assertEqual(catalogus_autorisatie2.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie2.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

    @tag("gh-1661")
    def test_load_initial_data_for_besluiten_api(self):
        """
        Test that it is possible to load existing CatalogusAutorisaties (along with
        regular Autorisaties) for Besluiten API
        """
        scopes = [str(SCOPE_BESLUITEN_AANMAKEN), str(SCOPE_BESLUITEN_ALLES_LEZEN)]
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            catalogus=self.catalogus,
            scopes=scopes,
        )
        besluittype = BesluitTypeFactory.create(concept=False)
        BesluitTypeFactory.create(concept=False)
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            besluittype=f"http://testserver/{_reverse(besluittype)}",
            scopes=[str(SCOPE_BESLUITEN_ALLES_LEZEN)],  # different scopes
        )

        response = self.client.get(self.url)

        # Regular Autorisatie with different scopes should be displayed separately
        expected_initial = [
            {
                "component": ComponentTypes.brc,
                "scopes": scopes,
                "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                "catalogi": [self.catalogus.pk],
            },
            {
                "component": ComponentTypes.brc,
                "scopes": [str(SCOPE_BESLUITEN_ALLES_LEZEN)],
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "besluittypen": {besluittype.pk},
                "externe_typen": [],
            },
        ]

        self.assertEqual(response.context["formset"].initial, expected_initial)

    @tag("gh-1661")
    def test_delete_catalogus_autorisaties(self):
        """
        Test that it is possible to delete existing CatalogusAutorisaties
        """
        scopes = [str(SCOPE_DOCUMENTEN_AANMAKEN), str(SCOPE_DOCUMENTEN_ALLES_LEZEN)]
        zaaktype = ZaakTypeFactory.create(concept=False)
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            catalogus=self.catalogus,
            scopes=scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            catalogus=zaaktype.catalogus,
            scopes=scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        response = self.client.get(self.url)

        expected_initial = [
            {
                "component": ComponentTypes.drc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                "catalogi": [self.catalogus.pk, zaaktype.catalogus.pk],
            }
        ]
        self.assertEqual(response.context["formset"].initial, expected_initial)

        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        catalogus_autorisatie = CatalogusAutorisatie.objects.get()

        self.assertEqual(catalogus_autorisatie.catalogus, self.catalogus)

    @tag("gh-1661")
    def test_regular_and_catalogus_autorisatie_with_different_va(self):
        """
        Test that it is possible to have regular and catalogus autorisaties exist, if they have
        different vertrouwelijkheidaanduiding
        """
        scopes = [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)]
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": scopes,
            "form-1-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-1-zaaktypen": [zaaktype.pk],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        autorisatie = Autorisatie.objects.get()
        catalogus_autorisatie = CatalogusAutorisatie.objects.get()

        # New autorisatie was created
        self.assertEqual(autorisatie.applicatie, self.applicatie)
        self.assertEqual(autorisatie.zaaktype, f"http://testserver{_reverse(zaaktype)}")
        self.assertEqual(autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie.scopes, scopes)
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        # New CatalogusAutorisatie was created
        self.assertEqual(catalogus_autorisatie.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

        # Load the page again to check if the initial data is as expected
        response = self.client.get(self.url)

        expected_initial = [
            {
                "component": ComponentTypes.zrc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                "catalogi": [self.catalogus.pk],
            },
            {
                "component": ComponentTypes.zrc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "zaaktypen": {zaaktype.pk},
                "externe_typen": [],
            },
        ]
        self.assertEqual(response.context["formset"].initial, expected_initial)

    @tag("gh-1661")
    def test_regular_and_catalogus_autorisatie_with_same_va(self):
        """
        Test that it is possible to have regular and catalogus autorisaties exist, if they have
        the same vertrouwelijkheidaanduiding

        They should show up in separate rows, they cannot be grouped in the same
        row because related_type_selection is different
        """
        scopes = [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)]
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": scopes,
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-1-component": ComponentTypes.zrc,
            "form-1-scopes": scopes,
            "form-1-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-1-zaaktypen": [zaaktype.pk],  # not from the same catalogus
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        autorisatie = Autorisatie.objects.get()
        catalogus_autorisatie = CatalogusAutorisatie.objects.get()

        # New autorisatie was created
        self.assertEqual(autorisatie.applicatie, self.applicatie)
        self.assertEqual(autorisatie.zaaktype, f"http://testserver{_reverse(zaaktype)}")
        self.assertEqual(autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie.scopes, scopes)
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

        # New CatalogusAutorisatie was created
        self.assertEqual(catalogus_autorisatie.applicatie, self.applicatie)
        self.assertEqual(catalogus_autorisatie.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(catalogus_autorisatie.scopes, scopes)
        self.assertEqual(
            catalogus_autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

        # Load the page again to check if the initial data is as expected
        response = self.client.get(self.url)

        expected_initial = [
            {
                "component": ComponentTypes.zrc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                "catalogi": [self.catalogus.pk],
            },
            {
                "component": ComponentTypes.zrc,
                "scopes": scopes,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                "zaaktypen": {zaaktype.pk},
                "externe_typen": [],
            },
        ]
        self.assertEqual(response.context["formset"].initial, expected_initial)

    @tag("gh-1661")
    def test_catalogus_autorisatie_switch_component(self):
        """
        Test that it is possible to switch the component of a catalogus autorisatie
        """
        scopes = [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)]
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeFactory.create(concept=False)
        # unrelated, should stay the same
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            zaaktype=f"http://testserver/{_reverse(zaaktype)}",
            scopes=[str(SCOPE_ZAKEN_BIJWERKEN)],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        # will be kept the same
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            catalogus=self.catalogus,
            scopes=[str(SCOPE_BESLUITEN_ALLES_LEZEN)],
        )
        # component will be changed
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            catalogus=self.catalogus,
            scopes=scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 3,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.zrc,
            "form-0-scopes": [str(SCOPE_ZAKEN_BIJWERKEN)],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-zaaktypen": [zaaktype.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
            "form-1-component": ComponentTypes.brc,
            "form-1-scopes": [str(SCOPE_BESLUITEN_ALLES_LEZEN)],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [self.catalogus.pk],
            "form-2-component": ComponentTypes.drc,
            "form-2-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-2-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-2-catalogi": [self.catalogus.pk],
            "form-2-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        autorisatie = Autorisatie.objects.get()
        unchanged, changed = CatalogusAutorisatie.objects.order_by("component")

        # autorisatie is the same
        self.assertEqual(autorisatie.applicatie, self.applicatie)
        self.assertEqual(autorisatie.zaaktype, f"http://testserver{_reverse(zaaktype)}")
        self.assertEqual(autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie.scopes, [str(SCOPE_ZAKEN_BIJWERKEN)])
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.geheim,
        )

        # brc CatalogusAutorisatie stays the same
        self.assertEqual(unchanged.applicatie, self.applicatie)
        self.assertEqual(unchanged.catalogus, self.catalogus)
        self.assertEqual(unchanged.component, ComponentTypes.brc)
        self.assertEqual(unchanged.scopes, [str(SCOPE_BESLUITEN_ALLES_LEZEN)])

        # New CatalogusAutorisatie was created for changed component
        self.assertEqual(changed.applicatie, self.applicatie)
        self.assertEqual(changed.catalogus, self.catalogus)
        self.assertEqual(changed.component, ComponentTypes.drc)
        self.assertEqual(changed.scopes, [str(SCOPE_DOCUMENTEN_AANMAKEN)])
        self.assertEqual(
            changed.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

    @tag("gh-1661")
    def test_catalogus_autorisaties_same_component_and_catalogus_different_scopes_should_fail(
        self,
    ):
        """
        It should not be possible to create two CatalogusAutorisaties with the same component
        and Catalogus, regardless of different scopes
        """
        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-1-component": ComponentTypes.drc,
            "form-1-scopes": [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [self.catalogus.pk],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["formset"]._non_form_errors[0],
            _(
                "You cannot create multiple Autorisaties/CatalogusAutorisaties with the "
                "same component and catalogus: {component}, {catalogus}"
            ).format(component=ComponentTypes.drc, catalogus=self.catalogus),
        )
        self.assertFalse(CatalogusAutorisatie.objects.exists())

    @tag("gh-1661")
    def test_regular_autorisatie_and_catalogus_autorisaties_same_component_and_catalogus_different_scopes_should_fail(
        self,
    ):
        """
        It should not be possible to create a CatalogusAutorisatie and a regular Autorisatie
        with a type from the same catalogus and the same component, even if the scopes are different
        """
        iot = InformatieObjectTypeFactory.create(concept=False)

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 3,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            # Unrelated autorisatie
            "form-0-component": ComponentTypes.ac,
            "form-0-scopes": [str(SCOPE_AUTORISATIES_BIJWERKEN)],
            "form-1-component": ComponentTypes.drc,
            "form-1-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-1-informatieobjecttypen": [iot.pk],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-2-component": ComponentTypes.drc,
            "form-2-scopes": [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)],
            "form-2-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-2-catalogi": [iot.catalogus.pk],
            "form-2-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["formset"]._non_form_errors[0],
            _(
                "You cannot create multiple Autorisaties/CatalogusAutorisaties with the "
                "same component and catalogus: {component}, {catalogus}"
            ).format(component=ComponentTypes.drc, catalogus=iot.catalogus),
        )
        self.assertFalse(CatalogusAutorisatie.objects.exists())

    @tag("gh-1661")
    def test_catalogus_autorisaties_same_component_and_catalogus_different_vertrouwelijkheidaanduing_should_fail(
        self,
    ):
        """
        It should not be possible to create two CatalogusAutorisaties with the same component,
        Catalogus and scopes, but different vertrouwelijkheidaanduiding
        """
        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-0-catalogi": [self.catalogus.pk],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-1-component": ComponentTypes.drc,
            "form-1-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [self.catalogus.pk],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["formset"]._non_form_errors[0],
            _("Scopes in {component} may not be duplicated.").format(
                component=ComponentTypes.drc
            ),
        )
        self.assertFalse(CatalogusAutorisatie.objects.exists())

    @tag("gh-1661")
    def test_autorisatie_with_type_catalogus_in_catalogus_autorisatie_should_fail(self):
        iot = InformatieObjectTypeFactory.create(
            concept=False, catalogus=self.catalogus
        )

        response = self.client.get(self.url)

        data = {
            # management form
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-informatieobjecttypen": {iot.pk},
            "form-0-externe_typen": [],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "form-1-component": ComponentTypes.drc,
            "form-1-scopes": [str(SCOPE_DOCUMENTEN_AANMAKEN)],
            "form-1-related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
            "form-1-catalogi": [self.catalogus.pk],
            "form-1-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["formset"]._non_form_errors[0],
            _("{field} may not have overlapping scopes.").format(
                field="informatieobjecttypen"
            ),
        )
        self.assertFalse(CatalogusAutorisatie.objects.exists())
        self.assertFalse(Autorisatie.objects.exists())

    def test_add_autorisatie_with_iotypen_without_catalogus(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1718

        When manual iotypen are added, the form should not fail
        """
        iot1, iot2 = InformatieObjectTypeFactory.create_batch(
            2, concept=False, catalogus=self.catalogus
        )
        data = {
            # management form
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-component": ComponentTypes.drc,
            "form-0-scopes": ["notificaties.consumeren"],
            "form-0-related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "form-0-informatieobjecttypen": [iot1.id, iot2.id],
            "form-0-vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.applicatie.autorisaties.count(), 2)
