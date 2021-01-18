# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import StatusTypeFactory
from openzaak.components.zaken.models import Status
from openzaak.utils.tests import AdminTestMixin

from ..factories import StatusFactory, ZaakFactory
from ..utils import get_operation_url


class StatusAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_status(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)

        add_url = reverse("admin:zaken_status_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_statustype": statustype.id,
            "datum_status_gezet_0": date(2018, 1, 1),
            "datum_status_gezet_1": time(10, 0, 0),
        }

        self.client.post(add_url, data)

        self.assertEqual(Status.objects.count(), 1)

        status = Status.objects.get()
        status_url = get_operation_url("status_read", uuid=status.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["datum_status_gezet"], "2018-01-01T10:00:00Z")

    def test_change_status(self):
        status = StatusFactory.create(statustoelichting="old")
        status_url = get_operation_url("status_read", uuid=status.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=status.zaak.uuid)
        change_url = reverse("admin:zaken_status_change", args=(status.pk,))
        data = {
            "uuid": status.uuid,
            "zaak": status.zaak.id,
            "_statustype": status.statustype.id,
            "datum_status_gezet_0": timezone.now().date(),
            "datum_status_gezet_1": timezone.now().time(),
            "statustoelichting": "new",
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        status.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["statustoelichting"], "old")
        self.assertEqual(new_data["statustoelichting"], "new")

    def test_delete_status_action(self):
        status = StatusFactory.create(statustoelichting="desc")
        status_url = get_operation_url("status_read", uuid=status.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=status.zaak.uuid)
        change_list_url = reverse("admin:zaken_status_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [status.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Status.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["statustoelichting"], "desc")

    def test_delete_status(self):
        status = StatusFactory.create(statustoelichting="desc")
        status_url = get_operation_url("status_read", uuid=status.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=status.zaak.uuid)
        delete_url = reverse("admin:zaken_status_delete", args=(status.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Status.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["statustoelichting"], "desc")
