# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils.admin import AdminTestMixin

from ...models import ZaakTypeInformatieObjectType
from ..factories import (
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


@tag("gh-1877")
@disable_admin_mfa()
class ZaakTypeInformatieObjectTypeDeleteAdminTests(AdminTestMixin, WebTest):
    def test_delete_published_ziot_not_allowed_if_documenten_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype,
            informatieobjecttype=non_concept_informatieobjecttype,
        )
        document = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=non_concept_informatieobjecttype
        )
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=non_concept_zaaktype, informatieobject=document.canonical
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_delete", args=(ziot.id,)
        )

        response = self.app.get(admin_url, status=403)

        # Deletion should not be allowed, because there are existing relations between
        # documenten and zaken that depend on the relation between their types
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 1)

    def test_delete_half_published_ziot_not_allowed_if_documenten_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype,
            informatieobjecttype=non_concept_informatieobjecttype,
        )
        document = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=non_concept_informatieobjecttype
        )
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=concept_zaaktype, informatieobject=document.canonical
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_delete", args=(ziot.id,)
        )

        response = self.app.get(admin_url, status=403)

        # Deletion should not be allowed, because there are existing relations between
        # documenten and zaken that depend on the relation between their types
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 1)

    def test_bulk_delete_published_ziots_not_allowed_if_documenten_related(
        self,
    ):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype,
            informatieobjecttype=non_concept_informatieobjecttype,
        )
        document = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=non_concept_informatieobjecttype
        )
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=non_concept_zaaktype, informatieobject=document.canonical
        )

        admin_url = reverse("admin:catalogi_zaaktypeinformatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [ziot.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(
            _("Zaak-Informatieobject-Type kan niet worden verwijderd"), response.text
        )
        self.assertIn(
            _(
                "uw account heeft geen rechten om de volgende typen objecten te verwijderen"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 1)

    def test_delete_published_ziot_allowed_if_no_documenten_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype,
            informatieobjecttype=non_concept_informatieobjecttype,
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_delete",
            args=(ziot.id,),
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # The relation is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_bulk_delete_published_ziots_allowed_if_no_documenten_related(
        self,
    ):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=non_concept_zaaktype,
            informatieobjecttype=non_concept_informatieobjecttype,
        )
        concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, zaaktypen=None
        )
        concept_ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype,
            informatieobjecttype=concept_informatieobjecttype,
        )

        admin_url = reverse("admin:catalogi_zaaktypeinformatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [ziot.id, concept_ziot.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_delete_concept_ziot_not_allowed_if_documenten_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype,
            informatieobjecttype=concept_informatieobjecttype,
        )

        document = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=concept_informatieobjecttype
        )
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=concept_zaaktype, informatieobject=document.canonical
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_delete",
            args=(concept_ziot.id,),
        )

        response = self.app.get(admin_url, status=403)

        # Deletion should not be allowed, because there are existing relations between
        # documenten and zaken that depend on the relation between their types
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 1)

    def test_bulk_delete_concept_ziots_not_allowed_if_documenten_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype1 = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot1 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype1,
            informatieobjecttype=concept_informatieobjecttype1,
        )
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype2 = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot2 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype2,
            informatieobjecttype=concept_informatieobjecttype2,
        )

        document = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=concept_informatieobjecttype1
        )
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=concept_zaaktype1, informatieobject=document.canonical
        )

        admin_url = reverse("admin:catalogi_zaaktypeinformatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_ziot1.id, concept_ziot2.id]

        response = form.submit()

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(
            _("Zaak-Informatieobject-Typen kan niet worden verwijderd"), response.text
        )
        self.assertIn(
            _(
                "uw account heeft geen rechten om de volgende typen objecten te verwijderen"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 2)

    def test_delete_concept_ziot_allowed_if_no_documenten_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype,
            informatieobjecttype=concept_informatieobjecttype,
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_delete",
            args=(concept_ziot.id,),
        )

        response = self.app.get(admin_url)

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # Both relaties are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_bulk_delete_concept_ziots_allowed_if_no_documenten_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype1 = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot1 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype1,
            informatieobjecttype=concept_informatieobjecttype1,
        )
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_informatieobjecttype2 = InformatieObjectTypeFactory.create(
            concept=True, zaaktypen=None
        )
        concept_ziot2 = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=concept_zaaktype2,
            informatieobjecttype=concept_informatieobjecttype2,
        )

        admin_url = reverse("admin:catalogi_zaaktypeinformatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_ziot1.id, concept_ziot2.id]

        response = form.submit()

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())
