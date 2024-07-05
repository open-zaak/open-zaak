# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import ZaakBesluit
from ..factories import ZaakFactory, ZaakInformatieObjectFactory


@disable_admin_mfa()
class ZaakAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.service = Service.objects.create(
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
