# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import Eigenschap, EigenschapSpecificatie
from ..factories import EigenschapSpecificatieFactory, ZaakTypeFactory


@disable_admin_mfa()
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

        response.forms["eigenschapspecificatie_form"].submit()

        specificatie.refresh_from_db()

        # Assert that the comma is still in place
        self.assertEqual(specificatie.waardenverzameling, ["some,comma", "bla"])

    def test_validation_length_comma_separated(self):
        form = self.app.get(reverse("admin:catalogi_eigenschapspecificatie_add")).forms[
            "eigenschapspecificatie_form"
        ]

        form["formaat"] = "getal"
        form["lengte"] = "5,3"
        form["kardinaliteit"] = "1"
        form["waardenverzameling"] = "Waarden"
        form.submit()

        new_specificatie = EigenschapSpecificatie.objects.get()
        self.assertEqual(new_specificatie.lengte, "5,3")


@tag("gh-1042")
@disable_admin_mfa()
class EigenschapAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_create_eigenschap_for_published_zaaktype_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        specificatie = EigenschapSpecificatieFactory.create(
            waardenverzameling=["some,comma", "bla"]
        )

        response = self.app.get(reverse("admin:catalogi_eigenschap_add"))

        form = response.forms["eigenschap_form"]

        form["eigenschapnaam"] = "foo"
        form["definitie"] = "bar"
        form["specificatie_van_eigenschap"] = specificatie.id
        form["toelichting"] = "baz"
        form["zaaktype"] = zaaktype.id
        response = form.submit()

        self.assertEqual(
            response.context["adminform"].errors,
            {
                "zaaktype": [
                    _(
                        "Creating a relation to non-concept {resource} is forbidden"
                    ).format(resource="zaaktype")
                ]
            },
        )
        self.assertEqual(Eigenschap.objects.count(), 0)
