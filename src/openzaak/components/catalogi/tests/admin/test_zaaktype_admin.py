from django.urls import reverse

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.selectielijst.tests import mock_oas_get, mock_resource_list
from openzaak.utils.tests import ClearCachesMixin

from ...models import ZaakType
from ..factories import CatalogusFactory, ZaakTypeFactory


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
            "https://referentielijsten-api.vng.cloud/api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
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
        form["doorlooptijd_behandeling"] = "12 00:00"
        form["opschorting_en_aanhouding_mogelijk"].select(False)
        form["verlenging_mogelijk"].select(False)
        form["vertrouwelijkheidaanduiding"].select("openbaar")
        form["producten_of_diensten"] = "https://example.com/foobarbaz"
        form["versiedatum"] = "21-11-2019"
        form["referentieproces_naam"] = "test"
        form["catalogus"] = catalogus.pk
        form["datum_begin_geldigheid"] = "21-11-2019"

        response = form.submit()

        # redirect on succesfull create, 200 on validation errors, 500 on db errors
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.count(), 1)
