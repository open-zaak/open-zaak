# SPDX-License-Identifier: EUPL-1.2
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from openzaak.components.documenten.admin import ObjectInformatieObjectAdmin
from openzaak.components.documenten.constants import ObjectInformatieObjectTypes
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObjectCanonical,
    ObjectInformatieObject,
)
from openzaak.components.zaken.tests.factories import ZaakFactory


class ObjectInformatieObjectAdminDeleteTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()

        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )

        self.canonical = EnkelvoudigInformatieObjectCanonical.objects.create()

        self.zaak = ZaakFactory.create()

        self.oio = ObjectInformatieObject.objects.create(
            informatieobject=self.canonical,
            object_type=ObjectInformatieObjectTypes.zaak,
            _zaak=self.zaak,
        )

        self.admin = ObjectInformatieObjectAdmin(
            ObjectInformatieObject,
            self.site,
        )

    def test_bulk_delete_action_is_disabled(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        actions = self.admin.get_actions(request)
        self.assertFalse(actions)

    def test_admin_individual_delete_objectinformatieobject(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        self.admin.delete_model(request, self.oio)
        self.assertEqual(ObjectInformatieObject.objects.count(), 0)
