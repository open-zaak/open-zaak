# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakObjectFactory

from ...models import ZaakObjectType
from ..factories import ZaakObjectTypeFactory, ZaakTypeFactory


@tag("gh-1877")
@disable_admin_mfa()
class ZaakObjectTypeDeleteAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_published_zaakobjecttype_not_allowed_if_resultaten_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=non_concept_zaaktype)
        ZaakObjectFactory.create(
            zaak__zaaktype=non_concept_zaaktype, zaakobjecttype=zaakobjecttype
        )

        admin_url = reverse(
            "admin:catalogi_zaakobjecttype_delete", args=(zaakobjecttype.id,)
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Zaakobjecttype kan niet worden verwijderd"), response.text)
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(ZaakObjectType.objects.count(), 1)

    def test_bulk_delete_published_zaakobjecttypen_not_allowed_if_resultaten_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype
        )

        ZaakObjectFactory.create(zaakobjecttype=non_concept_zaakobjecttype)

        admin_url = reverse("admin:catalogi_zaakobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_zaakobjecttype.id,
            non_concept_zaakobjecttype.id,
        ]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("Zaakobjecttypen kan niet worden verwijderd"), response.text)
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(ZaakObjectType.objects.count(), 2)

    def test_delete_published_zaakobjecttype_allowed_if_no_resultaten_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype
        )

        admin_url = reverse(
            "admin:catalogi_zaakobjecttype_delete",
            args=(non_concept_zaakobjecttype.id,),
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # zaakobjecttype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakObjectType.objects.exists())

    def test_bulk_delete_published_zaakobjecttypen_allowed_if_no_resultaten_related(
        self,
    ):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=concept_zaaktype)
        non_concept_zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype
        )

        admin_url = reverse("admin:catalogi_zaakobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_zaakobjecttype.id,
            non_concept_zaakobjecttype.id,
        ]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both zaakobjecttypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakObjectType.objects.exists())

    def test_delete_concept_zaakobjecttype_allowed_if_no_resultaten_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_zaakobjecttype_delete", args=(concept_zaakobjecttype.id,)
        )

        response = self.app.get(admin_url)

        # no warning, because all zaakobjecttypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # zaakobjecttype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakObjectType.objects.exists())

    def test_bulk_delete_concept_zaakobjecttypen_allowed_if_no_resultaten_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_zaakobjecttype1 = ZaakObjectTypeFactory.create(
            zaaktype=concept_zaaktype1
        )
        concept_zaakobjecttype2 = ZaakObjectTypeFactory.create(
            zaaktype=concept_zaaktype2
        )

        admin_url = reverse("admin:catalogi_zaakobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_zaakobjecttype1.id,
            concept_zaakobjecttype2.id,
        ]

        response = form.submit()

        # no warning, because all zaakobjecttypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both zaakobjecttypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakObjectType.objects.exists())
