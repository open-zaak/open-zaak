# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date
from unittest.mock import patch

from django.test import override_settings, tag
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext, gettext_lazy as _, ngettext_lazy

import requests_mock
from dateutil.relativedelta import relativedelta
from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import (
    mock_resource_get,
    mock_resource_list,
    mock_selectielijst_oas_get,
)
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import ClearCachesMixin, mock_nrc_oas_get

from ...models import ZaakType
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
    ZaakTypenRelatieFactory,
)


@disable_admin_mfa()
@requests_mock.Mocker()
class ZaaktypeAdminTests(
    NotificationsConfigMixin, SelectieLijstMixin, ClearCachesMixin, WebTest
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        selectielijst_config = ReferentieLijstConfig.get_solo()
        selectielijst_config.allowed_years = [2017, 2020]
        selectielijst_config.save()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_zaaktypen_list(self, m):
        ZaakTypeFactory.create()
        url = reverse("admin:catalogi_zaaktype_changelist")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

    def test_zaaktype_detail(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        zaaktype = ZaakTypeFactory.create()
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        # Verify that the save button is visible
        save_button = response.html.find("input", {"name": "_save"})
        self.assertIsNotNone(save_button)

    def test_selectielijst_procestype(self, m):
        """
        Test that the selectielijst procestype field is a dropdown.
        """
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        zaaktype = ZaakTypeFactory.create()
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["zaaktype_form"]
        field = form.fields["selectielijst_procestype"][0]
        self.assertEqual(field.tag, "select")
        # first element of JSON response
        self.assertEqual(
            field.value,
            "https://selectielijst.openzaak.nl/api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )

    def test_submit_zaaktype_required_fields(self, m):
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_zaaktype_add")
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        add_page = self.app.get(url)
        form = add_page.form

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
        form["referentieproces_naam"] = "test"
        form["catalogus"] = catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"
        form["verantwoordelijke"] = "063308836"

        response = form.submit()

        # redirect on successful create, 200 on validation errors, 500 on db errors
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.count(), 1)
        zaaktype = ZaakType.objects.get()
        self.assertEqual(zaaktype.trefwoorden, [])
        self.assertEqual(zaaktype.verantwoordingsrelatie, [])
        self.assertEqual(zaaktype.producten_of_diensten, [])

    @tag("gh-1306")
    def test_submit_zaaktype_identificatie_all_characters_allowed(self, m):
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_zaaktype_add")
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        add_page = self.app.get(url)
        form = add_page.form

        form["identificatie"] = "some zääktype"
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
        form["referentieproces_naam"] = "test"
        form["catalogus"] = catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"
        form["verantwoordelijke"] = "063308836"

        response = form.submit()

        # redirect on successful create, 200 on validation errors, 500 on db errors
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.count(), 1)
        zaaktype = ZaakType.objects.get()
        self.assertEqual(zaaktype.identificatie, "some zääktype")

    def test_doorlooptijd_behandeling_is_required(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")

        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        url = reverse("admin:catalogi_zaaktype_change", args=[zaaktype.pk])

        update_page = self.app.get(url)

        form = update_page.form
        form["vertrouwelijkheidaanduiding"].select("openbaar")
        form["doorlooptijd_behandeling_days"] = None
        form["doorlooptijd_behandeling_months"] = None
        form["doorlooptijd_behandeling_years"] = None

        response = form.submit()
        self.assertEqual(response.status_code, 200)

        response_form = response.context["adminform"].form
        self.assertIn(
            "Dit veld is verplicht.", response_form.errors["doorlooptijd_behandeling"]
        )

        form["doorlooptijd_behandeling_days"] = 12
        response = form.submit()
        self.assertEqual(response.status_code, 302)

    @tag("notifications")
    @override_settings(NOTIFICATIONS_DISABLED=False)
    @freeze_time("2019-11-01")
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_create_new_version(self, m, mock_notif):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_nrc_oas_get(m)
        m.post(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", status_code=201
        )
        startdate_old = date(2017, 1, 1)

        zaaktype_old = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype="",
            concept=False,
            datum_begin_geldigheid=startdate_old,
        )
        # reverse fk relations
        statustype_old = StatusTypeFactory.create(
            zaaktype=zaaktype_old, datum_begin_geldigheid=startdate_old
        )
        resultaattypeomschrijving = "https://example.com/resultaattypeomschrijving/1"
        m.register_uri("GET", resultaattypeomschrijving, json={"omschrijving": "init"})
        resultaattype_old = ResultaatTypeFactory.create(
            zaaktype=zaaktype_old,
            resultaattypeomschrijving=resultaattypeomschrijving,
            selectielijstklasse="",
            datum_begin_geldigheid=startdate_old,
        )
        roltype_old = RolTypeFactory.create(
            zaaktype=zaaktype_old, datum_begin_geldigheid=startdate_old
        )
        eigenschap_old = EigenschapFactory.create(
            zaaktype=zaaktype_old, datum_begin_geldigheid=startdate_old
        )
        zaaktypenrelatie_old = ZaakTypenRelatieFactory.create(zaaktype=zaaktype_old)
        # m2m relations
        besluittype = BesluitTypeFactory.create(zaaktypen=[zaaktype_old])
        informatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype_old
        ).informatieobjecttype
        # not copied
        ZaakFactory.create(zaaktype=zaaktype_old)
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype_old.pk,))

        get_response = self.app.get(url)

        form = get_response.form

        with self.captureOnCommitCallbacks(execute=True):
            post_response = form.submit("_addversion")

        zaaktype_new = ZaakType.objects.exclude(pk=zaaktype_old.pk).get()

        # check that the new zaak has the same identificator
        self.assertEqual(zaaktype_new.identificatie, zaaktype_old.identificatie)
        # check version dates
        self.assertEqual(zaaktype_new.datum_einde_geldigheid, None)
        self.assertEqual(zaaktype_new.datum_begin_geldigheid, date(2019, 11, 1))
        self.assertEqual(zaaktype_new.versiedatum, date(2019, 11, 1))
        self.assertTrue(zaaktype_new.concept)
        # response redirect to correct page
        self.assertEqual(
            post_response.location,
            reverse("admin:catalogi_zaaktype_change", args=(zaaktype_new.pk,)),
        )

        # assert the new relations are created
        self.assertNotEqual(zaaktype_new.statustypen.get().id, statustype_old.id)
        self.assertNotEqual(zaaktype_new.resultaattypen.get().id, resultaattype_old.id)
        self.assertNotEqual(zaaktype_new.roltype_set.get().id, roltype_old.id)
        self.assertNotEqual(zaaktype_new.eigenschap_set.get().id, eigenschap_old.id)
        self.assertNotEqual(
            zaaktype_new.zaaktypenrelaties.get().id, zaaktypenrelatie_old.id
        )
        # assert m2m relations are saved
        self.assertEqual(zaaktype_new.besluittypen.get().id, besluittype.id)
        self.assertEqual(
            zaaktype_new.informatieobjecttypen.get().id, informatieobjecttype.id
        )
        # assert new zaken are not created
        self.assertEqual(zaaktype_new.zaak_set.count(), 0)

        # Verify notification is sent
        zaaktype_new_url = reverse(
            "zaaktype-detail", kwargs={"uuid": zaaktype_new.uuid, "version": 1}
        )
        catalogus_url = reverse(
            "catalogus-detail",
            kwargs={"uuid": zaaktype_new.catalogus.uuid, "version": 1},
        )
        mock_notif.assert_called_with(
            {
                "aanmaakdatum": "2019-11-01T00:00:00Z",
                "actie": "create",
                "hoofdObject": f"http://testserver{zaaktype_new_url}",
                "kanaal": "zaaktypen",
                "resource": "zaaktype",
                "resourceUrl": f"http://testserver{zaaktype_new_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{catalogus_url}",
                },
            }
        )
        # assert that sub-resources have old datum_begin_geldigheid
        self.assertEqual(
            zaaktype_new.statustypen.get().datum_begin_geldigheid, startdate_old
        )
        self.assertEqual(
            zaaktype_new.resultaattypen.get().datum_begin_geldigheid, startdate_old
        )
        self.assertEqual(
            zaaktype_new.roltype_set.get().datum_begin_geldigheid, startdate_old
        )
        self.assertEqual(
            zaaktype_new.eigenschap_set.get().datum_begin_geldigheid, startdate_old
        )

    def test_create_new_version_fail_no_datum_einde_geldigheid(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")

        zaaktype_ = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype_.pk,))

        get_response = self.app.get(url)
        form = get_response.form
        post_response = form.submit("_addversion")

        error_message = post_response.html.find(class_="errorlist")
        self.assertIsNone(error_message)

    def test_submit_zaaktype_validate_doorlooptijd_servicenorm(self, m):
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_zaaktype_add")
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        add_page = self.app.get(url)
        form = add_page.form

        form["zaaktype_omschrijving"] = "test"
        form["doel"] = "test"
        form["aanleiding"] = "test"
        form["indicatie_intern_of_extern"].select("intern")
        form["handeling_initiator"] = "test"
        form["onderwerp"] = "test"
        form["handeling_behandelaar"] = "test"
        form["doorlooptijd_behandeling_days"] = 12
        form["servicenorm_behandeling_days"] = 15
        form["opschorting_en_aanhouding_mogelijk"].select(False)
        form["verlenging_mogelijk"].select(False)
        form["vertrouwelijkheidaanduiding"].select("openbaar")
        form["producten_of_diensten"] = "https://example.com/foobarbaz"
        form["referentieproces_naam"] = "test"
        form["catalogus"] = catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"

        response = form.submit()

        # redirect on succesfull create, 200 on validation errors, 500 on db errors
        self.assertEqual(response.status_code, 200)

        form = response.context["adminform"].form
        self.assertEqual(
            form.errors["__all__"],
            [
                "'Servicenorm behandeling' periode mag niet langer zijn dan "
                "de periode van 'Doorlooptijd behandeling'."
            ],
        )

    def test_add_zaaktype_page_without_selectielijst_client(self, *mocks):
        selectielijst_config = ReferentieLijstConfig.get_solo()
        selectielijst_config.service = None
        selectielijst_config.save()

        url = reverse("admin:catalogi_zaaktype_add")

        response = self.app.get(url)

        # Check that no 500 error is thrown
        self.assertEqual(response.status_code, 200)

        procestype_field = response.html.find(
            "input", {"id": "id_selectielijst_procestype"}
        )
        self.assertTrue(procestype_field.has_attr("disabled"))
        self.assertEqual(
            procestype_field.attrs["value"],
            _("Selectielijst configuration must be fixed first"),
        )

    def test_zaaktype_producten_of_diensten_empty_save(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        zaaktype = ZaakTypeFactory.create(producten_of_diensten=[])
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.form

        response = form.submit("_save")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            response.html.select_one(".field-producten_of_diensten .errorlist")
        )

    @freeze_time("2022-01-01T16:00Z")
    def test_filtering_on_validity(self, m):
        # create zaaktypen with different validities
        ZaakTypeFactory.create(
            zaaktype_omschrijving="zaaktype 1",
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 12, 31),
        )
        ZaakTypeFactory.create(
            zaaktype_omschrijving="zaaktype 2",
            datum_begin_geldigheid=date(2021, 1, 1),
            datum_einde_geldigheid=date(2022, 12, 31),
        )
        ZaakTypeFactory.create(
            zaaktype_omschrijving="zaaktype 3",
            datum_begin_geldigheid=date(2021, 1, 1),
            datum_einde_geldigheid=None,
        )
        ZaakTypeFactory.create(
            zaaktype_omschrijving="zaaktype 4",
            datum_begin_geldigheid=date(2022, 7, 1),
            datum_einde_geldigheid=None,
        )
        changelist_page = self.app.get(reverse("admin:catalogi_zaaktype_changelist"))

        with self.subTest("No validity filtering"):
            self.assertContains(changelist_page, "zaaktype 1")
            self.assertContains(changelist_page, "zaaktype 2")
            self.assertContains(changelist_page, "zaaktype 3")
            self.assertContains(changelist_page, "zaaktype 4")

        with self.subTest("filter currently valid"):
            response = changelist_page.click(description=gettext("Now"))

            self.assertNotContains(response, "zaaktype 1")
            self.assertContains(response, "zaaktype 2")
            self.assertContains(response, "zaaktype 3")
            self.assertNotContains(response, "zaaktype 4")

        with self.subTest("filter valid in the past"):
            response = changelist_page.click(description=gettext("Past"))

            self.assertContains(response, "zaaktype 1")
            self.assertNotContains(response, "zaaktype 2")
            self.assertNotContains(response, "zaaktype 3")
            self.assertNotContains(response, "zaaktype 4")

        with self.subTest("filter valid in the future"):
            response = changelist_page.click(description=gettext("Future"))

            self.assertNotContains(response, "zaaktype 1")
            self.assertNotContains(response, "zaaktype 2")
            self.assertNotContains(response, "zaaktype 3")
            self.assertContains(response, "zaaktype 4")

    def test_validate_changing_procestype_with_existing_resultaattypen(self, m):
        """
        Assert that the zaaktype procestype (selectielijst) stays consistent.

        Regression test for #970 -- changing the selectielijst procestype after
        resultaattypen have been made for the zaaktype is not supported, as this breaks
        the integrity (resultaattype selectielijstklasse must belong to
        zaaktype.selectielijst_procestype).
        """
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
        )
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["selectielijst_procestype"] = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )

        response = form.submit()
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].errors["selectielijst_procestype"]
        expected_error = _(
            "You cannot change the procestype because there are resultaatypen "
            "attached to this zaaktype with a selectielijstklasse belonging "
            "to the current procestype."
        )
        self.assertIn(expected_error, errors)

    def test_selectielijst_selectielijstklasse_missing_client_configuration(self, m):
        # the form may not validate if the selectielijstklasse data cannot be retrieved
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
        )
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        change_page = self.app.get(url)
        self.assertEqual(change_page.status_code, 200)

        with patch("zgw_consumers.client.build_client", return_value=None):
            response = change_page.form.submit()

            self.assertEqual(response.status_code, 200)  # instead of 302 for success
            expected_error = _("Could not build a client for {url}").format(
                url=selectielijst_resultaat
            )
            self.assertIn(
                expected_error, response.context["adminform"].errors["__all__"]
            )

    def test_reset_selectielijst_configuration(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
        )
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        self.assertEqual(response.status_code, 200)

        form = response.form
        # check that changing the procestype is now possible when we reset (that
        # validation needs to skip)
        form["selectielijst_reset"] = True
        form["selectielijst_procestype"] = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/96eae691-077f-4fd6-ad66-950b9b714880"
        )
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.selectielijst_procestype, "")
        resultaat = zaaktype.resultaattypen.get()
        self.assertEqual(resultaat.selectielijstklasse, "")

    @patch(
        "openzaak.components.catalogi.admin.zaaktypen.ReferentieLijstConfig.get_solo"
    )
    @tag("gh-1281")
    def test_default_selectielijst_year_regression(self, m, mock_solo):
        mock_solo.return_value = ReferentieLijstConfig(
            default_year=2017, allowed_years=[2017, 2020], service=self.service
        )

        mock_selectielijst_oas_get(m)
        mock_resource_list(
            m,
            resource="procestypen",
            query_map={
                "procestypen": {"jaar": 2017},
                "procestypen_2020": {"jaar": 2020},
            },
        )
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_zaaktype_add")

        # add a zaaktype
        add_page = self.app.get(url)
        form = add_page.form
        form["catalogus"].value = str(catalogus.id)
        form["zaaktype_omschrijving"] = "Test"
        form["doel"] = "Test"
        form["aanleiding"] = "Test"
        form["indicatie_intern_of_extern"].select("intern")
        form["vertrouwelijkheidaanduiding"].select("zaakvertrouwelijk")
        form["handeling_initiator"] = "Test"
        form["onderwerp"] = "Test"
        form["handeling_behandelaar"] = "Test"
        form["doorlooptijd_behandeling_years"] = "0"
        form["doorlooptijd_behandeling_months"] = "1"
        form["doorlooptijd_behandeling_days"] = "0"
        form["referentieproces_naam"] = "Test"
        form["datum_begin_geldigheid"] = "14-11-2022"
        form["verantwoordelijke"] = "063308836"

        # use non-default value
        form["selectielijst_procestype_jaar"].select("2020")

        # replace options with 2020 options, as the Javascript would do
        form["selectielijst_procestype"].options = [
            (
                "https://selectielijst.openzaak.nl/api/v1/procestypen/"
                "aa8aa2fd-b9c6-4e34-9a6c-58a677f60ea0",
                False,
                "Instellen en inrichten organisatie",
            ),
            (
                "https://selectielijst.openzaak.nl/api/v1/procestypen/"
                "f4603775-5a08-4829-85c8-28017dfeee1f",
                False,
                "Voorzieningen verstrekken",
            ),
        ]
        form["selectielijst_procestype"].select(
            "https://selectielijst.openzaak.nl/api/v1/procestypen/"
            "f4603775-5a08-4829-85c8-28017dfeee1f"
        )

        response = form.submit("_continue")
        self.assertEqual(response.status_code, 302)

        detail_page = response.follow()
        zaaktype = ZaakType.objects.get()
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2020)
        self.assertEqual(
            detail_page.form["selectielijst_procestype_jaar"].value, "2020"
        )
        label = next(
            label
            for opt, _, label in detail_page.form["selectielijst_procestype"].options
            if opt == detail_page.form["selectielijst_procestype"].value
        )
        self.assertEqual(label, "8 - Voorzieningen verstrekken")
        self.assertEqual(
            detail_page.form["selectielijst_procestype"].value,
            "https://selectielijst.openzaak.nl/api/v1/procestypen/"
            "f4603775-5a08-4829-85c8-28017dfeee1f",
        )

    def test_submit_zaaktype_with_no_catalogus(self, m):
        """
        Test that no catalogus ID provided causes a validation error and not an exception.
        Fixes #1474
        """
        url = reverse("admin:catalogi_zaaktype_add")
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        add_page = self.app.get(url)
        form = add_page.form

        response = form.submit()

        form = response.context["adminform"].form
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dit veld is verplicht.", form.errors["catalogus"])

    def test_submit_zaaktype_with_bad_catalogus(self, m):
        """
        Test that a bad catalogus ID causes a validation error and not an exception.
        Fixes #1474
        """
        url = reverse("admin:catalogi_zaaktype_add")
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        add_page = self.app.get(url)
        form = add_page.form

        form["catalogus"] = 16
        response = form.submit()

        form = response.context["adminform"].form
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Selecteer een geldige keuze. Deze keuze is niet beschikbaar.",
            form.errors["catalogus"],
        )


@disable_admin_mfa()
class ZaakTypePublishAdminTests(SelectieLijstMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

        self.catalogus = CatalogusFactory.create()
        self.url = reverse_lazy("admin:catalogi_zaaktype_changelist")
        self.query_params = {"catalogus_id__exact": self.catalogus.pk}

    @requests_mock.Mocker()
    def test_publish_selected_success(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(
            2,
            catalogus=self.catalogus,
            concept=True,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
            verlenging_mogelijk=False,
        )
        for zaaktype in zaaktype1, zaaktype2:
            StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
            StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
            ResultaatTypeFactory.create(
                zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
            )
            RolTypeFactory.create(zaaktype=zaaktype)

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [zaaktype1.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                ngettext_lazy(
                    "%d object has been published successfully",
                    "%d objects has been published successfully",
                    1,
                )
                % 1
            ],
        )

        zaaktype1.refresh_from_db()
        self.assertFalse(zaaktype1.concept)

        zaaktype2.refresh_from_db()
        self.assertTrue(zaaktype2.concept)

    def test_publish_already_selected(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [zaaktype.pk]

        response = form.submit()

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                ngettext_lazy(
                    "%d object is already published",
                    "%d objects are already published",
                    1,
                )
                % 1
            ],
        )

        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

    @requests_mock.Mocker()
    def test_publish_related_to_not_published(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            concept=True,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
            verlenging_mogelijk=False,
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)
        BesluitTypeFactory.create(
            zaaktypen=[zaaktype], catalogus=self.catalogus, concept=True
        )

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [zaaktype.pk]

        response = form.submit()

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                _("%(obj)s can't be published: %(error)s")
                % {
                    "obj": zaaktype,
                    "error": _("All related resources should be published"),
                }
            ],
        )

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

    @tag("gh-1085")
    def test_publish_missing_roltype(self):
        """
        Assert that at least one roltype exists.

        ImZTC prescribes a [1..*] cardinality. There's no requirements as far as I can
        see that there MUST be an initiator type.
        """
        zaaktype = ZaakTypeFactory.create(concept=True)
        publish_url = reverse("admin:catalogi_zaaktype_publish", args=(zaaktype.pk,))
        publish_page = self.app.get(publish_url)

        response = publish_page.form.submit()

        self.assertEqual(
            response.status_code, 200
        )  # no redirect because validation errors
        messages = list(response.context["messages"])

        error = _("Publishing a zaaktype requires at least one roltype to be defined.")
        self.assertIn(str(error), str(messages[0]))

    @tag("gh-1085")
    def test_publish_requires_at_least_two_statustypes(self):
        """
        Assert that a zaaktype can only be published if there are at least two status types.

        ImZTC prescribes at least one, but this doesn't make sense in the context of the
        standard - a case must be created with an initial status (the single statustype).
        But a case is also closed by setting the last statustype (based on
        ``StatusType.volgNummer``). However, doing that requires a ``resultaat`` to be
        set, which should logically only be possible after the case was started (by
        setting the initial status). This means that the initial status cannot be the
        final status, thus we require at least 2 statustypen for a zaaktype.
        """
        zaaktype = ZaakTypeFactory.create(concept=True)
        publish_url = reverse("admin:catalogi_zaaktype_publish", args=(zaaktype.pk,))
        publish_page = self.app.get(publish_url)

        error = _(
            "Publishing a zaaktype requires at least two statustypes to be defined."
        )

        with self.subTest("no statustypen"):
            response = publish_page.form.submit("_publish")

            self.assertEqual(
                response.status_code, 200
            )  # no redirect because validation errors
            messages = list(response.context["messages"])

            self.assertIn(str(error), str(messages[0]))

        with self.subTest("one statustype"):
            StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)

            response = publish_page.form.submit("_publish")

            self.assertEqual(
                response.status_code, 200
            )  # no redirect because validation errors
            messages = list(response.context["messages"])

            self.assertIn(str(error), str(messages[0]))

    @tag("gh-1085")
    def test_publish_requires_at_least_once_resultaattype(self):
        """
        Assert that at least one resultaattype must exist before publishing a zaaktype.
        """
        zaaktype = ZaakTypeFactory.create(concept=True)
        publish_url = reverse("admin:catalogi_zaaktype_publish", args=(zaaktype.pk,))
        publish_page = self.app.get(publish_url)

        response = publish_page.form.submit()

        self.assertEqual(
            response.status_code, 200
        )  # no redirect because validation errors
        messages = list(response.context["messages"])

        error = _(
            "Publishing a zaaktype requires at least one resultaattype to be defined."
        )
        self.assertIn(str(error), str(messages[0]))

    @tag("gh-1085")
    @requests_mock.Mocker()
    def test_publish_with_minimum_requirements(self, m):
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
            ),
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)

        publish_url = reverse("admin:catalogi_zaaktype_publish", args=(zaaktype.pk,))
        publish_page = self.app.get(publish_url)
        response = publish_page.form.submit()

        self.assertEqual(response.status_code, 302)

    @tag("gh-1085")
    def test_bulk_publish_action_validation(self):
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="#1085",
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [zaaktype.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        messages = [str(m) for m in response.follow().context["messages"]]
        expected_messages = [
            _("Publishing a zaaktype requires at least one roltype to be defined."),
            _(
                "Publishing a zaaktype requires at least one resultaattype to be defined."
            ),
            _("Publishing a zaaktype requires at least two statustypes to be defined."),
        ]
        for expected_error in expected_messages:
            with self.subTest(error=expected_error):
                full_error = _("%(obj)s can't be published: %(error)s") % {
                    "obj": zaaktype,
                    "error": expected_error,
                }
                self.assertIn(full_error, messages)

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

    @tag("gh-1264")
    @override_settings(
        NOTIFICATIONS_DISABLED=True, ALLOWED_HOSTS=["testserver", "example.com"]
    )
    @requests_mock.Mocker()
    def test_save_published_zaaktype(self, m):
        """Regressiontest where a user is not able to save a published zaaktype"""

        # from test_publish_with_minimum_requirements
        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        procestype = "https://selectielijst.openzaak.nl/api/v1/procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
        zaaktype = ZaakTypeFactory.create(
            concept=False,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(procestype),
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)

        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "procestypen", url=procestype)

        admin_url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        change_page = self.app.get(admin_url)
        for operation in ["_save", "_addanother", "_continue", "_addversion"]:
            with self.subTest(operation=operation):
                change_page.form["datum_einde_geldigheid"] = "2020-01-01"
                response = change_page.form.submit(operation)
                zaaktype.refresh_from_db()

                self.assertEqual(response.status_code, 302)
                self.assertEqual(zaaktype.datum_einde_geldigheid, date(2020, 1, 1))

                zaaktype.datum_einde_geldigheid = None
                zaaktype.save()

        change_page.form["datum_einde_geldigheid"] = "2020-01-01"
        response = change_page.form.submit("_export")
        zaaktype.refresh_from_db()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.content_type, "application/zip")
        self.assertEqual(zaaktype.datum_einde_geldigheid, date(2020, 1, 1))

    @tag("gh-1275")
    @override_settings(NOTIFICATIONS_DISABLED=True)
    @requests_mock.Mocker()
    def test_save_published_zaaktype_with_verlenging_mogelijk(self, m):
        """Regressiontest where a user is not able to publish a concept-zaaktype with a verlenging"""

        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        procestype = "https://selectielijst.openzaak.nl/api/v1/procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
        zaaktype = ZaakTypeFactory.create(
            concept=True,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(procestype),
            verlenging_mogelijk=True,
            verlengingstermijn=relativedelta(days=42),
            doorlooptijd_behandeling=relativedelta(days=42),
            servicenorm_behandeling=relativedelta(days=42),
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)

        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "procestypen", url=procestype)

        publish_url = reverse("admin:catalogi_zaaktype_publish", args=(zaaktype.pk,))
        publish_page = self.app.get(publish_url)
        response = publish_page.form.submit().follow()
        zaaktype.refresh_from_db()
        self.assertNotContains(
            response,
            "'verlengingstermijn' must be set if 'verlenging_mogelijk' is set.",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(zaaktype.concept, False)

    @override_settings(NOTIFICATIONS_DISABLED=True)
    @requests_mock.Mocker()
    def test_published_zaaktype_with_empty_durations(self, m):
        """Regression test where a user is not able to publish a concept-zaaktype with a verlenging"""

        mock_selectielijst_oas_get(m)
        mock_resource_list(m, "procestypen")
        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "resultaten", url=selectielijst_resultaat)
        procestype = "https://selectielijst.openzaak.nl/api/v1/procestypen/cdb46f05-0750-4d83-8025-31e20408ed21"
        zaaktype = ZaakTypeFactory.create(
            concept=False,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            selectielijst_procestype=(procestype),
            doorlooptijd_behandeling=relativedelta(),
        )
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=1)
        StatusTypeFactory.create(zaaktype=zaaktype, statustypevolgnummer=2)
        ResultaatTypeFactory.create(
            zaaktype=zaaktype, selectielijstklasse=selectielijst_resultaat
        )
        RolTypeFactory.create(zaaktype=zaaktype)

        selectielijst_resultaat = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
        )
        mock_resource_get(m, "procestypen", url=procestype)

        admin_url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        change_page = self.app.get(admin_url)
        self.assertNotContains(change_page, "relativedelta")
        self.assertEqual(zaaktype.doorlooptijd_behandeling, relativedelta())
        self.assertEqual(zaaktype.servicenorm_behandeling, None)

    def test_related_object_links(self):
        """
        test that links to related objects in admin list page are valid
        """
        ZaakTypeFactory.create(identificatie="some")
        list_url = reverse("admin:catalogi_zaaktype_changelist")

        response = self.app.get(list_url)

        self.assertEqual(response.status_code, 200)
        rel_object_links = (
            response.html.find(id="result_list")
            .find(class_="field-_get_object_actions")
            .find_all("a")
        )
        self.assertEqual(len(rel_object_links), 7)
        for link in rel_object_links:
            url = link["href"]
            with self.subTest(url):
                response = self.app.get(url)
                self.assertEqual(response.status_code, 200)
