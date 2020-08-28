# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import EigenschapSpecificatieFactory


class EigenschapSpecificatieAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_change_eigenschap_specificatie(self):
        specificatie = EigenschapSpecificatieFactory.create(
            waardenverzameling=["some,comma", "bla"]
        )

        response = self.app.get(
            reverse(
                "admin:catalogi_eigenschapspecificatie_change", args=(specificatie.pk,)
            )
        )

        response.form.submit()

        specificatie.refresh_from_db()

        # Assert that the comma is still in place
        self.assertEqual(specificatie.waardenverzameling, ["some,comma", "bla"])
