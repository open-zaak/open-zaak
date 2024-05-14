# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import BesluitFactory


@disable_admin_mfa()
class BesluitAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_non_alphanumeric_identificatie_validation(self):
        """
        Edit a zaak with an identificatie allowed by the API.

        This should not trigger validation errors.
        """
        besluit = BesluitFactory.create(identificatie="ZK bläh")
        url = reverse("admin:besluiten_besluit_change", args=(besluit.pk,))
        response = self.app.get(url)
        self.assertEqual(response.form["identificatie"].value, "ZK bläh")

        submit_response = response.form.submit()

        self.assertEqual(submit_response.status_code, 302)
