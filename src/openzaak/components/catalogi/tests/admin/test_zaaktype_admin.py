from datetime import date

from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from freezegun import freeze_time

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.selectielijst.tests import mock_oas_get, mock_resource_list
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
class ZaaktypeAdminTests(ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

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

    @freeze_time("2019-11-01")
    def test_create_new_version(self, m):
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")

        zaaktype_old = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
        )
        # reverse fk relations
        statustype_old = StatusTypeFactory.create(zaaktype=zaaktype_old)
        resultaattype_old = ResultaatTypeFactory.create(zaaktype=zaaktype_old)
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
