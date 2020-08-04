# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.components.zaken.models import Rol
from openzaak.utils.tests import AdminTestMixin

from ..factories import RolFactory, ZaakFactory
from ..utils import get_operation_url


class RolAdminTests(AdminTestMixin, WebTest):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_create_rol(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create()
        add_url = reverse("admin:zaken_rol_add")

        get_response = self.app.get(add_url)

        form = get_response.form

        form["zaak"] = zaak.id
        form["_roltype"] = roltype.id
        form["betrokkene_type"] = "natuurlijk_persoon"
        form["betrokkene"] = "http://example.com/betrokkene/1"
        form["roltoelichting"] = "desc"

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=zaak.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["roltoelichting"], "desc")

    def test_change_rol(self):
        rol = RolFactory.create(roltoelichting="old")
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        change_url = reverse("admin:zaken_rol_change", args=(rol.pk,))

        get_response = self.app.get(change_url)

        form = get_response.form
        form["roltoelichting"] = "new"

        form.submit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        rol.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["roltoelichting"], "old")
        self.assertEqual(new_data["roltoelichting"], "new")

    def test_delete_rol_action(self):
        rol = RolFactory.create(roltoelichting="some desc")
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        change_list_url = reverse("admin:zaken_rol_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [rol.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Rol.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["roltoelichting"], "some desc")

    def test_delete_rol(self):
        rol = RolFactory.create(roltoelichting="some desc")
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        delete_url = reverse("admin:zaken_rol_delete", args=(rol.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Rol.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["roltoelichting"], "some desc")
