# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

import requests_mock
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from django_webtest import WebTest
from freezegun import freeze_time

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_oas_get, mock_resource_list
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import mock_nrc_oas_get
from openzaak.utils.tests import ClearCachesMixin

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


@requests_mock.Mocker()
class ZaaktypeAdminTests(ReferentieLijstServiceMixin, ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
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
        mock_oas_get(m)
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
        mock_oas_get(m)
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
        mock_oas_get(m)
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
        form["producten_of_diensten"] = "https://example.com/foobarbaz"
        form["referentieproces_naam"] = "test"
        form["catalogus"] = catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"

        response = form.submit()

        # redirect on succesfull create, 200 on validation errors, 500 on db errors
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.count(), 1)

    @override_settings(NOTIFICATIONS_DISABLED=False)
    @freeze_time("2019-11-01")
    def test_create_new_version(self, m):
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_nrc_oas_get(m)
        m.post(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", status_code=201
        )

        zaaktype_old = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
        )
        # reverse fk relations
        statustype_old = StatusTypeFactory.create(zaaktype=zaaktype_old)
        resultaattypeomschrijving = "https://example.com/resultaattypeomschrijving/1"
        m.register_uri("GET", resultaattypeomschrijving, json={"omschrijving": "init"})
        resultaattype_old = ResultaatTypeFactory.create(
            zaaktype=zaaktype_old, resultaattypeomschrijving=resultaattypeomschrijving
        )
        roltype_old = RolTypeFactory.create(zaaktype=zaaktype_old)
        eigenschap_old = EigenschapFactory.create(zaaktype=zaaktype_old)
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
        form["datum_einde_geldigheid"] = "2019-01-01"

        with capture_on_commit_callbacks(execute=True):
            post_response = form.submit("_addversion")

        zaaktype_old.refresh_from_db()

        self.assertEqual(zaaktype_old.datum_einde_geldigheid, date(2019, 1, 1))

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
        called_urls = [item.url for item in m.request_history]
        self.assertIn(
            "https://notificaties-api.vng.cloud/api/v1/notificaties", called_urls
        )

    def test_create_new_version_fail_no_datum_einde_geldigheid(self, m):
        mock_oas_get(m)
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
        self.assertIn(
            "datum_einde_geldigheid is required if the new version is being created",
            error_message.text,
        )

    def test_submit_zaaktype_validate_doorlooptijd_servicenorm(self, m):
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_zaaktype_add")
        mock_oas_get(m)
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

    @patch("vng_api_common.models.ClientConfig.get_client", return_value=None)
    def test_add_zaaktype_page_without_selectielijst_client(self, *mocks):
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
        mock_oas_get(m)
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


class ZaakTypePublishAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

        self.catalogus = CatalogusFactory.create()
        self.url = reverse_lazy("admin:catalogi_zaaktype_changelist")
        self.query_params = {"catalogus_id__exact": self.catalogus.pk}

    def test_publish_selected_success(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=self.catalogus)

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [zaaktype1.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(messages, ["1 object has been published successfully"])

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
        self.assertEqual(messages, ["1 object is already published"])

        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

    def test_publish_related_to_not_published(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus, concept=True)
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
                f"{zaaktype} can't be published: All related resources should be published"
            ],
        )

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)
