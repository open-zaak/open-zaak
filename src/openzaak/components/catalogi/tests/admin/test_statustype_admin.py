# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.zaken.tests.factories import StatusFactory
from openzaak.tests.utils.admin import AdminTestMixin

from ...models import StatusType
from ..factories import StatusTypeFactory, ZaakTypeFactory


@tag("gh-1042")
@disable_admin_mfa()
class StatusTypeAdminTests(AdminTestMixin, WebTest):
    def test_create_statustype_for_published_zaaktype_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.app.get(reverse("admin:catalogi_statustype_add"))

        form = response.forms["statustype_form"]

        form["statustype_omschrijving"] = "foo"
        form["statustypevolgnummer"] = 1
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
        self.assertEqual(StatusType.objects.count(), 0)


@tag("gh-1877")
@disable_admin_mfa()
class StatusTypeDeleteAdminTests(AdminTestMixin, WebTest):
    def test_delete_published_statustype_not_allowed_if_statussen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        statustype = StatusTypeFactory.create(zaaktype=non_concept_zaaktype)
        StatusFactory.create(zaak__zaaktype=non_concept_zaaktype, statustype=statustype)

        admin_url = reverse("admin:catalogi_statustype_delete", args=(statustype.id,))

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Statustype kan niet worden verwijderd"), response.text)
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(StatusType.objects.count(), 1)

    def test_bulk_delete_published_statustypen_not_allowed_if_statussen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_statustype = StatusTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_statustype = StatusTypeFactory.create(zaaktype=non_concept_zaaktype)

        StatusFactory.create(statustype=non_concept_statustype)

        admin_url = reverse("admin:catalogi_statustype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_statustype.id, non_concept_statustype.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Statustypen kan niet worden verwijderd"), response.text)
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(StatusType.objects.count(), 2)

    def test_delete_published_statustype_allowed_if_no_statussen_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_statustype = StatusTypeFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_statustype_delete", args=(non_concept_statustype.id,)
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # statustype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StatusType.objects.exists())

    def test_bulk_delete_published_statustypen_allowed_if_no_statussen_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_statustype = StatusTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_statustype = StatusTypeFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_statustype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_statustype.id, non_concept_statustype.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both statustypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StatusType.objects.exists())

    def test_delete_concept_statustype_allowed_if_no_statussen_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_statustype = StatusTypeFactory.create(zaaktype=concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_statustype_delete", args=(concept_statustype.id,)
        )

        response = self.app.get(admin_url)

        # no warning, because all statussen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # statustype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StatusType.objects.exists())

    def test_bulk_delete_concept_statustypen_allowed_if_no_statussen_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_statustype1 = StatusTypeFactory.create(zaaktype=concept_zaaktype1)
        concept_statustype2 = StatusTypeFactory.create(zaaktype=concept_zaaktype2)

        admin_url = reverse("admin:catalogi_statustype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_statustype1.id, concept_statustype2.id]

        response = form.submit()

        # no warning, because all statussen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both statustypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StatusType.objects.exists())
