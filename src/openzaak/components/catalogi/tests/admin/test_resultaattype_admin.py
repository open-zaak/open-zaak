# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlencode

from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.translation import ugettext as _

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory, UserFactory
from openzaak.selectielijst.tests import (
    _get_base_url,
    mock_oas_get,
    mock_resource_get,
    mock_resource_list,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.utils.tests import ClearCachesMixin

from ...models import ResultaatType
from ..factories import ResultaatTypeFactory, ZaakTypeFactory


@requests_mock.Mocker()
class ResultaattypeAdminTests(ReferentieLijstServiceMixin, ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_zaaktypen_list(self, m):
        ResultaatTypeFactory.create()
        url = reverse("admin:catalogi_resultaattype_changelist")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

    def test_resultaattype_detail(self, m):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        mock_resource_get(m, "procestypen", procestype_url)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__selectielijst_procestype=procestype_url
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(resultaattype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        # Verify that the save button is visible
        save_button = response.html.find("input", {"name": "_save"})
        self.assertIsNotNone(save_button)

    def test_selectielijst_selectielijstklasse(self, m):
        """
        Test that the selectielijst procestype field is a dropdown.
        """
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        mock_resource_get(m, "procestypen", procestype_url)
        zaaktype = ResultaatTypeFactory.create(
            zaaktype__selectielijst_procestype=procestype_url
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["resultaattype_form"]
        field = form.fields["selectielijstklasse"][0]
        self.assertEqual(field.tag, "input")
        # first element of JSON response
        self.assertEqual(
            field._value,
            "https://selectielijst.openzaak.nl/api/v1/resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
        )

    def test_resultaattype_detail_with_read_only_user(self, m):
        user = UserFactory.create(is_staff=True)
        view_resultaattype = Permission.objects.get(codename="view_resultaattype")
        user.user_permissions.add(view_resultaattype)
        self.app.set_user(user)

        selectielijst_api = "https://selectielijst.openzaak.nl/api/v1/"
        procestype_url = (
            f"{selectielijst_api}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        resultaat_url = (
            f"{selectielijst_api}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        omschrijving_url = (
            "https://referentielijsten-api.vng.cloud/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        mock_resource_get(m, "procestypen", procestype_url)
        mock_resource_get(m, "resultaten", resultaat_url)
        mock_resource_get(m, "resultaattypeomschrijvingen", omschrijving_url)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__selectielijst_procestype=procestype_url,
            selectielijstklasse=resultaat_url,
            resultaattypeomschrijving=omschrijving_url,
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(resultaattype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

    def test_edit_resultaattype_selectielijst_filtered_by_procestype(self, m):
        """
        Test that the selectielijst procestype field is a dropdown.
        """
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")

        selectielijstklasse_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/d92e5a77-c523-4273-b8e0-c912115ef156"
        )
        m.get(
            f"{_get_base_url()}resultaten?{urlencode({'procesType': procestype_url})}",
            json={
                "count": 100,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "algemeenBestuurEnInrichtingOrganisatie": True,
                        "alleTaakgebieden": False,
                        "bedrijfsvoeringEnPersoneel": True,
                        "bewaartermijn": "P5Y",
                        "burgerzaken": True,
                        "economie": False,
                        "generiek": True,
                        "heffenBelastingen": False,
                        "herkomst": "Risicoanalyse",
                        "naam": "Niet doorgegaan",
                        "nummer": 4,
                        "omschrijving": "",
                        "onderwijs": False,
                        "procesType": procestype_url,
                        "procestermijn": "nihil",
                        "procestermijnOpmerking": "",
                        "procestermijnWeergave": "Nihil",
                        "publiekeInformatieEnRegistratie": False,
                        "sociaalDomein": False,
                        "specifiek": False,
                        "sportCultuurEnRecreatie": False,
                        "toelichting": "",
                        "url": selectielijstklasse_url,
                        "veiligheid": False,
                        "verkeerEnVervoer": False,
                        "vhrosv": False,
                        "volksgezonheidEnMilieu": False,
                        "volledigNummer": "1.4",
                        "waardering": "vernietigen",
                    },
                ],
            },
        )
        mock_resource_get(m, "procestypen", procestype_url)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__selectielijst_procestype=procestype_url
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(resultaattype.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["resultaattype_form"]

        zaaktype_procestype = (
            response.html("div", {"class": "field-get_zaaktype_procestype"})[0]
            .find_all("div")[-1]
            .text
        )
        self.assertEqual(zaaktype_procestype, "1 - Instellen en inrichten organisatie")

        field = form.fields["selectielijstklasse"][0]

        self.assertEqual(field.tag, "input")
        self.assertEqual(len(field.options), 1)
        # first element of JSON response
        self.assertEqual(
            field._value,
            "https://selectielijst.openzaak.nl/api/v1/resultaten/d92e5a77-c523-4273-b8e0-c912115ef156",
        )

    def test_create_resultaattype_selectielijst_filtered_by_procestype(self, m):
        """
        Test that the selectielijst procestype field is a dropdown.
        """
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")

        selectielijstklasse_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/d92e5a77-c523-4273-b8e0-c912115ef156"
        )
        m.get(
            f"{_get_base_url()}resultaten?{urlencode({'procesType': procestype_url})}",
            json={
                "count": 100,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "algemeenBestuurEnInrichtingOrganisatie": True,
                        "alleTaakgebieden": False,
                        "bedrijfsvoeringEnPersoneel": True,
                        "bewaartermijn": "P5Y",
                        "burgerzaken": True,
                        "economie": False,
                        "generiek": True,
                        "heffenBelastingen": False,
                        "herkomst": "Risicoanalyse",
                        "naam": "Niet doorgegaan",
                        "nummer": 4,
                        "omschrijving": "",
                        "onderwijs": False,
                        "procesType": procestype_url,
                        "procestermijn": "nihil",
                        "procestermijnOpmerking": "",
                        "procestermijnWeergave": "Nihil",
                        "publiekeInformatieEnRegistratie": False,
                        "sociaalDomein": False,
                        "specifiek": False,
                        "sportCultuurEnRecreatie": False,
                        "toelichting": "",
                        "url": selectielijstklasse_url,
                        "veiligheid": False,
                        "verkeerEnVervoer": False,
                        "vhrosv": False,
                        "volksgezonheidEnMilieu": False,
                        "volledigNummer": "1.4",
                        "waardering": "vernietigen",
                    },
                ],
            },
        )
        mock_resource_get(m, "procestypen", procestype_url)

        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=procestype_url)
        query_params = urlencode(
            {
                "zaaktype__id__exact": zaaktype.id,
                "zaaktype": zaaktype.id,
                "catalogus": zaaktype.catalogus.pk,
            }
        )
        url = f"{reverse('admin:catalogi_resultaattype_add')}?_changelist_filters={query_params}"

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["resultaattype_form"]

        zaaktype_procestype = (
            response.html("div", {"class": "field-get_zaaktype_procestype"})[0]
            .find_all("div")[-1]
            .text
        )
        self.assertEqual(zaaktype_procestype, "1 - Instellen en inrichten organisatie")

        field = form.fields["selectielijstklasse"][0]

        self.assertEqual(field.tag, "input")
        self.assertEqual(len(field.options), 1)
        # first element of JSON response
        self.assertEqual(
            field._value,
            "https://selectielijst.openzaak.nl/api/v1/resultaten/d92e5a77-c523-4273-b8e0-c912115ef156",
        )

    def test_create_resultaattype_selectielijst_bewaartermijn_null(self, m):
        """
        Test if creating a resultaattype with selectielijstklasse.bewaartermijn
        = null is possible
        """
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        selectielijstklasse_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/8320ab7d-3a8d-4c8b-b94a-14b4fa374d0a"
        )
        omschrijving_url = (
            "https://referentielijsten-api.vng.cloud/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )

        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        mock_resource_get(m, "procestypen", procestype_url)
        mock_resource_get(m, "resultaten", selectielijstklasse_url)
        mock_resource_get(m, "resultaattypeomschrijvingen", omschrijving_url)

        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=procestype_url)

        url = reverse("admin:catalogi_resultaattype_add")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["resultaattype_form"]
        form["zaaktype"] = zaaktype.pk
        form["omschrijving"] = "test"
        form["selectielijstklasse"] = selectielijstklasse_url
        form["resultaattypeomschrijving"] = omschrijving_url
        form["brondatum_archiefprocedure_afleidingswijze"] = "ingangsdatum_besluit"
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResultaatType.objects.count(), 1)
        self.assertEqual(ResultaatType.objects.first().omschrijving, "test")

    def test_resultaattype_detail_no_procestype(self, m):
        procestype_url = ""
        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__selectielijst_procestype=procestype_url
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(resultaattype.pk,))

        response = self.app.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertIn(
            _(
                "Please select a Procestype for the related ZaakType to get "
                "proper filtering of selectielijstklasses"
            ),
            response.text,
        )
