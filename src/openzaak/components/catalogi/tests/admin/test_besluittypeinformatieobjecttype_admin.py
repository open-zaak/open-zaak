# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.tests.utils.admin import AdminTestMixin

from ...models import BesluitTypeInformatieObjectType
from ..factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)
from ..factories.relatieklassen import BesluitTypeInformatieObjectTypeFactory


@disable_admin_mfa()
class BesluitTypeInformatieObjectTypeAdminTests(AdminTestMixin, WebTest):
    def test_create_relation(self):
        besluittype = BesluitTypeFactory.create(concept=True)
        iotype = InformatieObjectTypeFactory.create(
            catalogus=besluittype.catalogus, zaaktypen=None
        )

        response = self.app.get(
            reverse("admin:catalogi_besluittypeinformatieobjecttype_add"),
            {"besluittype": besluittype.pk},
        )
        form = response.forms["besluittypeinformatieobjecttype_form"]
        form["_informatieobjecttype"] = iotype.pk
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        relation = BesluitTypeInformatieObjectType.objects.get()
        self.assertEqual(relation.besluittype, besluittype)
        self.assertEqual(relation._informatieobjecttype, iotype)

    def test_create_relation_without_informatieobjecttype(self):
        besluittype = BesluitTypeFactory.create(concept=True)

        response = self.app.get(
            reverse("admin:catalogi_besluittypeinformatieobjecttype_add"),
            {"besluittype": besluittype.pk},
        )
        response = response.forms["besluittypeinformatieobjecttype_form"].submit()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BesluitTypeInformatieObjectType.objects.exists())
        self.assertIn("Je moet een informatieobjecttype opgeven", response.text)

    def test_change_relation_of_concept_besluittype(self):
        relation = BesluitTypeInformatieObjectTypeFactory.create(
            besluittype__concept=True
        )

        response = self.app.get(
            reverse(
                "admin:catalogi_besluittypeinformatieobjecttype_change",
                args=(relation.pk,),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("_save", response.text)

    def test_change_relation_of_published_besluittype_is_read_only(self):
        relation = BesluitTypeInformatieObjectTypeFactory.create(
            besluittype__concept=False
        )

        response = self.app.get(
            reverse(
                "admin:catalogi_besluittypeinformatieobjecttype_change",
                args=(relation.pk,),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_save", response.text)
