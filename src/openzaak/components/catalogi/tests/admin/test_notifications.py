# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import ClearCachesMixin

from ...models import BesluitType, InformatieObjectType, ZaakType
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)


@tag("notifications")
@disable_admin_mfa()
@override_settings(NOTIFICATIONS_DISABLED=False)
@freeze_time("2022-01-01")
@patch("notifications_api_common.viewsets.send_notification.delay")
class NotificationAdminTests(
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

        cls.catalogus = CatalogusFactory.create()
        cls.catalogus_url = reverse(
            "catalogus-detail", kwargs={"uuid": cls.catalogus.uuid, "version": 1}
        )

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_informatieobjecttype_notify_on_create(self, mock_notif):
        url = reverse("admin:catalogi_informatieobjecttype_add")

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
        iotype_url = reverse(
            "informatieobjecttype-detail", kwargs={"uuid": iotype.uuid, "version": 1}
        )
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
            }
        )

    def test_informatieobjecttype_notify_on_change(self, mock_notif):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True,
            omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            catalogus=self.catalogus,
        )
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]
        form["omschrijving"] = "different-test"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        iotype_url = reverse(
            "informatieobjecttype-detail",
            kwargs={"uuid": informatieobjecttype.uuid, "version": 1},
        )
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
            }
        )

    def test_no_informatieobjecttype_notify_on_no_change(self, mock_notif):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True, omschrijving="test", vertrouwelijkheidaanduiding="openbaar"
        )
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        mock_notif.assert_not_called()

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
            "besluittype-detail", kwargs={"uuid": besluittype.uuid, "version": 1}
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
            }
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
            "besluittype-detail", kwargs={"uuid": besluittype.uuid, "version": 1}
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
            }
        )

    def test_besluit_no_notify_on_no_change(self, mock_notif):
        besluit = BesluitTypeFactory.create(concept=True, omschrijving="test")
        url = reverse("admin:catalogi_besluittype_change", args=(besluit.pk,))

        response = self.app.get(url)
        form = response.forms["besluittype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        mock_notif.assert_not_called()

    def test_zaaktype_notify_on_create(self, mock_notif):
        url = reverse("admin:catalogi_zaaktype_add")

        response = self.app.get(url)

        form = response.forms["zaaktype_form"]
        form["zaaktype_omschrijving"] = "test"
        form["doel"] = "test"
        form["aanleiding"] = "test"
        form["indicatie_intern_of_extern"].select("intern")
        form["handeling_initiator"] = "test"
        form["onderwerp"] = "test"
        form["handeling_behandelaar"] = "test"
        form["doorlooptijd_behandeling_days"] = 12
        form["opschorting_en_aanhouding_mogelijk"].select(False)
        form["verlenging_mogelijk"].select(False)
        form["vertrouwelijkheidaanduiding"].select("openbaar")
        form["producten_of_diensten"] = "https://example.com/foobarbaz"
        form["referentieproces_naam"] = "test"
        form["catalogus"] = self.catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"
        form["verantwoordelijke"] = "063308836"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        zaaktype = ZaakType.objects.get()
        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": zaaktype.uuid, "version": 1}
        )
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{zaaktype_url}",
                "kanaal": "zaaktypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "create",
                "resource": "zaaktype",
                "resourceUrl": f"http://testserver{zaaktype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            }
        )

    def test_zaaktype_notify_on_change(self, mock_notif):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            catalogus=self.catalogus,
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        form["zaaktype_omschrijving"] = "different-test"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": zaaktype.uuid, "version": 1}
        )
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{zaaktype_url}",
                "kanaal": "zaaktypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "update",
                "resource": "zaaktype",
                "resourceUrl": f"http://testserver{zaaktype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            }
        )

    def test_zaaktype_no_notify_on_no_change(self, mock_notif):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_save")

        mock_notif.assert_not_called()

    def test_zaaktype_notify_correct_resource_url_on_new_version(self, mock_notif):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        zaaktype_old = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            catalogus=self.catalogus,
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype_old.pk,))

        response = self.app.get(url)
        form = response.form
        form["datum_einde_geldigheid"] = "2021-01-01"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit("_addversion")

        zaaktype_old.refresh_from_db()
        zaaktype_new = ZaakType.objects.exclude(pk=zaaktype_old.pk).get()

        zaaktype_new_url = reverse(
            "zaaktype-detail", kwargs={"uuid": zaaktype_new.uuid, "version": 1}
        )
        mock_notif.assert_called_with(
            {
                "hoofdObject": f"http://testserver{zaaktype_new_url}",
                "kanaal": "zaaktypen",
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "create",
                "resource": "zaaktype",
                "resourceUrl": f"http://testserver{zaaktype_new_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{self.catalogus_url}",
                },
            }
        )
