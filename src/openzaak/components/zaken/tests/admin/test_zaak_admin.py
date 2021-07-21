# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import ZaakBesluit
from ..factories import ZaakFactory, ZaakInformatieObjectFactory


class ZaakAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_zaaktype_detail_external_io_not_available(self):
        zaak = ZaakFactory.create()
        zio = ZaakInformatieObjectFactory.create(zaak=zaak)
        zio._informatieobject = None
        zio._informatieobject_url = "http://bla.com/404"
        zio.save()

        url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        with requests_mock.Mocker() as m:
            m.get("http://bla.com/404", status_code=404, json={})
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("http://bla.com/404", response.text)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_zaaktype_detail_external_besluit_not_available(self):
        zaak = ZaakFactory.create()
        ZaakBesluit.objects.create(zaak=zaak, _besluit_url="http://bla.com/404")

        url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        with requests_mock.Mocker() as m:
            m.get("http://bla.com/404", status_code=404, json={})
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("http://bla.com/404", response.text)

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
