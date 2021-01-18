# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import EigenschapSpecificatie
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

    def test_validation_length_comma_separated(self):
        form = self.app.get(reverse("admin:catalogi_eigenschapspecificatie_add")).form

        form["formaat"] = "getal"
        form["lengte"] = "5,3"
        form["kardinaliteit"] = "1"
        form["waardenverzameling"] = "Waarden"
        form.submit()

        new_specificatie = EigenschapSpecificatie.objects.get()
        self.assertEqual(new_specificatie.lengte, "5,3")
