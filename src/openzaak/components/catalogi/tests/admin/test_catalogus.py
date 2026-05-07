# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakFactory

from ...models import Catalogus
from ..factories import CatalogusFactory, ZaakTypeFactory, ZaakTypenRelatieFactory


@disable_admin_mfa()
class CatalogusAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_catalogus_list_name(self):
        CatalogusFactory.create(naam="test")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "test")

    def test_catalogus_list_placeholder_name(self):
        CatalogusFactory.create(naam="")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "(onbekend)")

    def test_related_object_links(self):
        """
        test that links to related objects in admin list page are valid
        """
        CatalogusFactory.create(naam="test")
        list_url = reverse("admin:catalogi_catalogus_changelist")

        response = self.app.get(list_url)

        self.assertEqual(response.status_code, 200)
        rel_object_links = (
            response.html.find(id="result_list")
            .find(class_="field-_get_object_actions")
            .find_all("a")
        )
        self.assertEqual(len(rel_object_links), 3)
        for link in rel_object_links:
            url = link["href"]
            with self.subTest(url):
                response = self.app.get(url)
                self.assertEqual(response.status_code, 200)


@tag("gh-1877")
@disable_admin_mfa()
class CatalogusDeleteAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_catalogus_with_published_zaaktype_not_allowed_if_zaken_related(
        self,
    ):
        catalogus = CatalogusFactory.create()
        non_concept_zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=catalogus
        )

        ZaakFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_catalogus_delete", args=(catalogus.id,))

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("catalogus kan niet worden verwijderd"), response.text)
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(Catalogus.objects.count(), 1)

    def test_bulk_delete_catalogus_with_published_zaaktypen_not_allowed_if_zaken_related(
        self,
    ):
        catalogus = CatalogusFactory.create()
        ZaakTypeFactory.create(concept=True, catalogus=catalogus)
        non_concept_zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=catalogus
        )

        ZaakFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_catalogus_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [catalogus.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(_("catalogus kan niet worden verwijderd"), response.text)
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(Catalogus.objects.count(), 1)

    def test_delete_catalogus_with_published_zaaktype_allowed_if_no_zaken_related(self):
        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=catalogus)

        # Relations should not block deletion
        ZaakTypenRelatieFactory.create(zaaktype=zaaktype)
        ZaakTypeFactory.create(concept=False, catalogus=catalogus)

        admin_url = reverse("admin:catalogi_catalogus_delete", args=(catalogus.id,))

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # Both Zaaktypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Catalogus.objects.exists())

    def test_bulk_delete_catalogus_with_published_zaaktypen_allowed_if_no_zaken_related(
        self,
    ):
        catalogus = CatalogusFactory.create()
        ZaakTypeFactory.create(concept=True, catalogus=catalogus)
        ZaakTypeFactory.create(concept=False, catalogus=catalogus)

        admin_url = reverse("admin:catalogi_catalogus_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [catalogus.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # catalogus is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Catalogus.objects.exists())

    def test_delete_catalogus_with_concept_zaaktype_allowed_if_no_zaken_related(self):
        catalogus = CatalogusFactory.create()
        ZaakTypeFactory.create(concept=True, catalogus=catalogus)

        admin_url = reverse("admin:catalogi_catalogus_delete", args=(catalogus.id,))

        response = self.app.get(admin_url)

        # no warning, because all zaaktypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # catalogus is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Catalogus.objects.exists())

    def test_bulk_delete_catalogus_with_concept_zaaktypen_allowed_if_no_zaken_related(
        self,
    ):
        catalogus1 = CatalogusFactory.create()
        catalogus2 = CatalogusFactory.create()
        ZaakTypeFactory.create(concept=True, catalogus=catalogus1)
        ZaakTypeFactory.create(concept=True, catalogus=catalogus2)

        admin_url = reverse("admin:catalogi_catalogus_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [catalogus1.id, catalogus2.id]

        response = form.submit()

        # no warning, because all zaaktypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # catalogi are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Catalogus.objects.exists())
