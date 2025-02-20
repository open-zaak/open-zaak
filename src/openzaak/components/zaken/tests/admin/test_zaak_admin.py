# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from urllib.parse import urlencode

from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories.resultaattype import (
    ResultaatTypeFactory,
)
from openzaak.components.catalogi.tests.factories.statustype import StatusTypeFactory
from openzaak.components.catalogi.tests.factories.zaaktype import ZaakTypeFactory
from openzaak.components.zaken.models.betrokkenen import (
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
)

from ...models import ZaakBesluit
from ..factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)


@disable_admin_mfa()
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.service = ServiceFactory.create(
            api_type=APITypes.drc,
            api_root="https://external.nl/api/v1/",
        )

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_zaaktype_detail_external_io_not_available(self):
        zaak = ZaakFactory.create()
        zio = ZaakInformatieObjectFactory.create(zaak=zaak)
        zio._informatieobject = None
        zio._informatieobject_base_url = self.service
        zio._informatieobject_relative_url = "io/404"
        zio.save()

        url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        with requests_mock.Mocker() as m:
            m.get("https://external.nl/api/v1/io/404", status_code=404, json={})
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("https://external.nl/api/v1/io/404", response.text)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_zaaktype_detail_external_besluit_not_available(self):
        zaak = ZaakFactory.create()
        ZaakBesluit.objects.create(
            zaak=zaak,
            _besluit_base_url=self.service,
            _besluit_relative_url="besluiten/404",
        )

        url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        with requests_mock.Mocker() as m:
            m.get("https://external.nl/api/v1/besluiten/404", status_code=404, json={})
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("https://external.nl/api/v1/besluiten/404", response.text)

    def test_non_alphanumeric_identificatie_validation(self):
        """
        Edit a zaak with an identificatie allowed by the API.

        This should not trigger validation errors.
        """
        zaak = ZaakFactory.create(identificatie="ZK bläh")
        url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))
        response = self.app.get(url)
        self.assertEqual(response.form["identificatie"].value, "ZK bläh")

        submit_response = response.form.submit()

        self.assertEqual(submit_response.status_code, 302)

    def test_related_object_links(self):
        """
        test that links to related objects in admin list page are valid
        """
        ZaakFactory.create(identificatie="some")
        zaak_list_url = reverse("admin:zaken_zaak_changelist")

        response = self.app.get(zaak_list_url)

        self.assertEqual(response.status_code, 200)
        rel_object_links = (
            response.html.find(id="result_list")
            .find(class_="field-_get_object_actions")
            .find_all("a")
        )
        self.assertEqual(len(rel_object_links), 10)
        for link in rel_object_links:
            url = link["href"]
            with self.subTest(url):
                response = self.app.get(url)
                self.assertEqual(response.status_code, 200)

    def test_changelist_values_local(self):
        """
        Tests that the ZAAK's result, status and zaaktype are shown on the changelist
        view. These should only be shown when the values are stored locally in the db.
        """
        zaaktype = ZaakTypeFactory(identificatie="Zaaktype XYZ")
        resultaattype = ResultaatTypeFactory(omschrijving="Resultaat XYZ")
        statustype = StatusTypeFactory(
            zaaktype=zaaktype, statustype_omschrijving="Omschrijving XYZ"
        )

        zaak = ZaakFactory.create(identificatie="some", zaaktype=zaaktype)

        ResultaatFactory(zaak=zaak, resultaattype=resultaattype)
        StatusFactory(statustype=statustype)

        zaak_list_url = reverse("admin:zaken_zaak_changelist")

        with requests_mock.Mocker() as request_mocker:
            response = self.app.get(zaak_list_url)

        self.assertFalse(request_mocker.called)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, resultaattype.omschrijving)
        self.assertContains(response, zaaktype.identificatie)
        self.assertContains(response, statustype.statustype_omschrijving)

    def test_changelist_values_remote(self):
        """
        Tests that the ZAAK's result, status and zaaktype are shown on the changelist
        view. These should only be shown when the values are stored locally in the db.
        """
        zaaktype_uuid = "eae1791c-2f23-48c7-bae5-1a83574b67fe"
        zaaktype = f"{self.service.api_root}zaken/{zaaktype_uuid}"
        resultaattype = (
            f"{self.service.api_root}/resultaten/67161be9-f386-4b20-a3e4-47ff6fdfd57e"
        )
        statustype = (
            f"{self.service.api_root}/statustypen/e5754fe2-83ac-431f-8e72-fe6dc063b92b"
        )

        ZaakFactory.create(identificatie="some", zaaktype=zaaktype)

        ResultaatFactory(resultaattype=resultaattype)
        StatusFactory(statustype=statustype)

        zaak_list_url = reverse("admin:zaken_zaak_changelist")

        with requests_mock.Mocker() as request_mocker:
            response = self.app.get(zaak_list_url)

        self.assertFalse(request_mocker.called)

        self.assertEqual(response.status_code, 200)

    def test_create_with_external_zaaktype(self):
        """
        Add a zaak with an external zaaktype
        """
        zaak_add_url = reverse("admin:zaken_zaak_add")

        response = self.app.get(zaak_add_url)

        form = response.form
        form["_zaaktype_base_url"] = self.service.pk
        form["_zaaktype_relative_url"] = "zaken/c10edbb4-d038-4333-a9ba-bbccfc8fa8bd"
        form["vertrouwelijkheidaanduiding"] = VertrouwelijkheidsAanduiding.openbaar
        form["bronorganisatie"] = "517439943"
        form["identificatie"] = "ZAAK1"
        form["verantwoordelijke_organisatie"] = "517439943"
        form["startdatum"] = "2023-01-01"
        form["registratiedatum"] = "2023-01-01"

        submit_response = form.submit()

        self.assertEqual(submit_response.status_code, 302)

    def test_zaaktype_omschrijving_search(self):
        """
        Search for zaken with the given zaaktype__zaaktype_omschrijving
        """
        external_zaaktype = (
            "https://external.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        # zaak with external zaaktype
        ZaakFactory(zaaktype=external_zaaktype, identificatie="zaak-external")

        zaaktype = ZaakTypeFactory(zaaktype_omschrijving="foobar")
        # zaak with internal zaaktype
        ZaakFactory.create(zaaktype=zaaktype, identificatie="zaak-XYZ")

        with requests_mock.Mocker() as requests_mocker:
            response = self.app.get(reverse("admin:zaken_zaak_changelist"))

            form = response.forms["changelist-search"]
            form["q"] = "foobar"

            submit_response = form.submit()

        self.assertEqual(requests_mocker.request_history, [])
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "zaak-XYZ")
        self.assertNotContains(submit_response, "zaak-external")

    def test_zaaktype_identificatie_search(self):
        """
        Search for zaken with the given zaaktype__identificatie
        """
        external_zaaktype = (
            "https://external.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        # zaak with external zaaktype
        ZaakFactory(zaaktype=external_zaaktype, identificatie="zaak-external")

        zaaktype = ZaakTypeFactory(identificatie="internal-zaaktype")
        # zaak with internal zaaktype
        ZaakFactory.create(zaaktype=zaaktype, identificatie="zaak-XYZ")

        with requests_mock.Mocker() as requests_mocker:
            response = self.app.get(reverse("admin:zaken_zaak_changelist"))

            form = response.forms["changelist-search"]
            form["q"] = "internal-zaaktype"

            submit_response = form.submit()

        self.assertEqual(requests_mocker.request_history, [])
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "zaak-XYZ")
        self.assertNotContains(submit_response, "zaak-external")

    def test_filter_on_betrokkene_bsn(self):
        rol = RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )

        NatuurlijkPersoon.objects.create(
            rol=rol, inp_bsn="129117729"
        )  # http://www.wilmans.com/sofinummer/

        zaak_list_url = reverse("admin:zaken_zaak_changelist")

        query_params = urlencode({"q": 129117729})

        response = self.app.get(f"{zaak_list_url}?{query_params}")
        result_list = response.html.find(id="result_list")
        identificatie_element = result_list.find(class_="field-identificatie")

        self.assertEqual(identificatie_element.text, rol.zaak.identificatie)

    def test_filter_on_betrokkene_rsin(self):
        rol = RolFactory.create(
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )

        NietNatuurlijkPersoon.objects.create(rol=rol, inn_nnp_id="129117729")

        zaak_list_url = reverse("admin:zaken_zaak_changelist")

        query_params = urlencode({"q": 129117729})

        response = self.app.get(f"{zaak_list_url}?{query_params}")
        result_list = response.html.find(id="result_list")
        identificatie_element = result_list.find(class_="field-identificatie")

        self.assertEqual(identificatie_element.text, rol.zaak.identificatie)
