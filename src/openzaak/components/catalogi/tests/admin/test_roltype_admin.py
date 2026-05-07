# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.constants import RolOmschrijving

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import RolFactory
from openzaak.tests.utils.admin import AdminTestMixin

from ...models import RolType
from ..factories import RolTypeFactory, ZaakTypeFactory


@tag("gh-1042")
@disable_admin_mfa()
class RolTypeAdminTests(AdminTestMixin, WebTest):
    def test_create_roltype_for_published_zaaktype_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.app.get(reverse("admin:catalogi_roltype_add"))
        form = response.forms["roltype_form"]

        form["omschrijving"] = "foo"
        form["omschrijving_generiek"] = RolOmschrijving.adviseur
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
        self.assertEqual(RolType.objects.count(), 0)

    def test_update_roltype_published_zaaktype_fail_validation(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create()

        response = self.app.get(
            reverse("admin:catalogi_roltype_change", args=(roltype.pk,))
        )
        form = response.forms["roltype_form"]
        form["omschrijving"] = "foo"
        form["omschrijving_generiek"] = RolOmschrijving.adviseur
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
        self.assertIn("zaaktype", response.forms[1].fields)

        roltype.refresh_from_db()

        self.assertNotEqual(roltype.zaaktype, zaaktype)


@tag("gh-1877")
@disable_admin_mfa()
class RolTypeDeleteAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_published_roltype_not_allowed_if_rollen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create(zaaktype=non_concept_zaaktype)
        RolFactory.create(zaak__zaaktype=non_concept_zaaktype, roltype=roltype)

        admin_url = reverse("admin:catalogi_roltype_delete", args=(roltype.id,))

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Roltype kan niet worden verwijderd"), response.text)
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(RolType.objects.count(), 1)

    def test_bulk_delete_published_roltypen_not_allowed_if_rollen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_roltype = RolTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_roltype = RolTypeFactory.create(zaaktype=non_concept_zaaktype)

        RolFactory.create(roltype=non_concept_roltype)

        admin_url = reverse("admin:catalogi_roltype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_roltype.id, non_concept_roltype.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Roltypen kan niet worden verwijderd"), response.text)
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(RolType.objects.count(), 2)

    def test_delete_published_roltype_allowed_if_no_rollen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_roltype = RolTypeFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_roltype_delete", args=(non_concept_roltype.id,)
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # roltype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RolType.objects.exists())

    def test_bulk_delete_published_roltypen_allowed_if_no_rollen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_roltype = RolTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_roltype = RolTypeFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_roltype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_roltype.id, non_concept_roltype.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both roltypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RolType.objects.exists())

    def test_delete_concept_roltype_allowed_if_no_rollen_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_roltype = RolTypeFactory.create(zaaktype=concept_zaaktype)

        admin_url = reverse("admin:catalogi_roltype_delete", args=(concept_roltype.id,))

        response = self.app.get(admin_url)

        # no warning, because all roltypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # roltype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RolType.objects.exists())

    def test_bulk_delete_concept_roltypen_allowed_if_no_rollen_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_roltype1 = RolTypeFactory.create(zaaktype=concept_zaaktype1)
        concept_roltype2 = RolTypeFactory.create(zaaktype=concept_zaaktype2)

        admin_url = reverse("admin:catalogi_roltype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_roltype1.id, concept_roltype2.id]

        response = form.submit()

        # no warning, because all roltypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both roltypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RolType.objects.exists())
