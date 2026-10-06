# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.models.zaken import ZaakBesluit
from openzaak.components.zaken.tests.factories import ZaakFactory

from ..factories import BesluitFactory


@disable_admin_mfa()
class BesluitAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_sync_zaakbesluit_valid_form(self):
        besluit = BesluitFactory.create(identificatie="1234abcd")
        zaak = ZaakFactory.create()

        self.assertFalse(ZaakBesluit.objects.exists())
        url = reverse("admin:besluiten_besluit_change", args=(besluit.pk,))
        response = self.app.get(url)
        form = response.forms["besluit_form"]
        form["_zaak"] = zaak.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ZaakBesluit.objects.exists())

        obj = ZaakBesluit.objects.get()
        self.assertEqual(obj.zaak, zaak)
        self.assertEqual(obj.besluit, besluit)

    def test_non_alphanumeric_identificatie_validation(self):
        """
        Edit a zaak with an identificatie allowed by the API.

        This should not trigger validation errors.
        """
        besluit = BesluitFactory.create(identificatie="ZK bläh")
        url = reverse("admin:besluiten_besluit_change", args=(besluit.pk,))
        response = self.app.get(url)
        form = response.forms["besluit_form"]

        self.assertEqual(form["identificatie"].value, "ZK bläh")
        submit_response = form.submit()

        self.assertEqual(submit_response.status_code, 302)
