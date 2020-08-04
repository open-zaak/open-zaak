# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.zaken.models import ZaakObject
from openzaak.utils.tests import AdminTestMixin

from ..factories import ZaakFactory, ZaakObjectFactory
from ..utils import get_operation_url


class ZaakObjectAdminTests(AdminTestMixin, WebTest):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_create_zaakobject(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        add_url = reverse("admin:zaken_zaakobject_add")

        get_response = self.app.get(add_url)

        form = get_response.form
        form["zaak"] = zaak.id
        form["object"] = "http://example.com/adres/1"
        form["object_type"] = "adres"

        form.submit()

        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["object_type"], "adres")

    def test_change_zaakobject(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        change_url = reverse("admin:zaken_zaakobject_change", args=(zaakobject.pk,))

        get_response = self.app.get(change_url)

        form = get_response.form
        form["object"] = "http://example.com/adres/2"

        form.submit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaakobject.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["object"], "http://example.com/adres/1")
        self.assertEqual(new_data["object"], "http://example.com/adres/2")

    def test_delete_zaakobject_action(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        change_list_url = reverse("admin:zaken_zaakobject_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [zaakobject.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(ZaakObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["object"], "http://example.com/adres/1")

    def test_delete_zaakobject(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        delete_url = reverse("admin:zaken_zaakobject_delete", args=(zaakobject.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(ZaakObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["object"], "http://example.com/adres/1")
