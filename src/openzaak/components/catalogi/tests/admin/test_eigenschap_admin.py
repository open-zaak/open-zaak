# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakEigenschapFactory

from ...models import Eigenschap, EigenschapSpecificatie
from ..factories import (
    EigenschapFactory,
    EigenschapSpecificatieFactory,
    ZaakTypeFactory,
)


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


@tag("gh-1877")
@disable_admin_mfa()
class EigenschapDeleteAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_published_eigenschap_not_allowed_if_zaakeigenschappen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        eigenschap = EigenschapFactory.create(zaaktype=non_concept_zaaktype)
        ZaakEigenschapFactory.create(
            zaak__zaaktype=non_concept_zaaktype, eigenschap=eigenschap
        )

        admin_url = reverse("admin:catalogi_eigenschap_delete", args=(eigenschap.id,))

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Eigenschap kan niet worden verwijderd"), response.text)
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(Eigenschap.objects.count(), 1)

    def test_bulk_delete_published_eigenschappen_not_allowed_if_zaakeigenschappen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_eigenschap = EigenschapFactory.create(zaaktype=concept_zaaktype)
        non_concept_eigenschap = EigenschapFactory.create(zaaktype=non_concept_zaaktype)

        ZaakEigenschapFactory.create(eigenschap=non_concept_eigenschap)

        admin_url = reverse("admin:catalogi_eigenschap_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_eigenschap.id, non_concept_eigenschap.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Eigenschappen kan niet worden verwijderd"), response.text)
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(Eigenschap.objects.count(), 2)

    def test_delete_published_eigenschap_allowed_if_no_zaakeigenschappen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_eigenschap = EigenschapFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_eigenschap_delete", args=(non_concept_eigenschap.id,)
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # eigenschap is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Eigenschap.objects.exists())

    def test_bulk_delete_published_eigenschappen_allowed_if_no_zaakeigenschappen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_eigenschap = EigenschapFactory.create(zaaktype=concept_zaaktype)
        non_concept_eigenschap = EigenschapFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_eigenschap_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_eigenschap.id, non_concept_eigenschap.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both eigenschappen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Eigenschap.objects.exists())

    def test_delete_concept_eigenschap_allowed_if_no_zaakeigenschappen_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_eigenschap = EigenschapFactory.create(zaaktype=concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_eigenschap_delete", args=(concept_eigenschap.id,)
        )

        response = self.app.get(admin_url)

        # no warning, because all eigenschappen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # eigenschap is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Eigenschap.objects.exists())

    def test_bulk_delete_concept_eigenschappen_allowed_if_no_zaakeigenschappen_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_eigenschap1 = EigenschapFactory.create(zaaktype=concept_zaaktype1)
        concept_eigenschap2 = EigenschapFactory.create(zaaktype=concept_zaaktype2)

        admin_url = reverse("admin:catalogi_eigenschap_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_eigenschap1.id, concept_eigenschap2.id]

        response = form.submit()

        # no warning, because all eigenschappen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both eigenschappen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Eigenschap.objects.exists())
