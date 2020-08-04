# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.utils.tests import AdminTestMixin

from ..factories import ZaakFactory, ZaakInformatieObjectFactory
from ..utils import get_operation_url


class ZaakInformatieObjectAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_zaakinformatieobject(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        informatieobject = EnkelvoudigInformatieObjectFactory.create()

        add_url = reverse("admin:zaken_zaakinformatieobject_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_informatieobject": informatieobject.canonical.id,
            "aard_relatie": "hoort_bij",
            "beschrijving": "description",
        }

        self.client.post(add_url, data)

        self.assertEqual(ZaakInformatieObject.objects.count(), 1)

        zaakinformatieobject = ZaakInformatieObject.objects.get()
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["beschrijving"], "description")

    def test_change_zaakinformatieobject(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create(beschrijving="old")
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakinformatieobject.zaak.uuid)
        change_url = reverse(
            "admin:zaken_zaakinformatieobject_change", args=(zaakinformatieobject.pk,)
        )
        data = {
            "uuid": zaakinformatieobject.uuid,
            "zaak": zaakinformatieobject.zaak.id,
            "_informatieobject": zaakinformatieobject.informatieobject.id,
            "aard_relatie": zaakinformatieobject.aard_relatie,
            "beschrijving": "new",
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaakinformatieobject.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["beschrijving"], "old")
        self.assertEqual(new_data["beschrijving"], "new")

    def test_delete_zaakinformatieobject_action(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create(
            beschrijving="description"
        )
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakinformatieobject.zaak.uuid)
        change_list_url = reverse("admin:zaken_zaakinformatieobject_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [zaakinformatieobject.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(ZaakInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["beschrijving"], "description")

    def test_delete_zaakinformatieobject(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create(
            beschrijving="description"
        )
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakinformatieobject.zaak.uuid)
        delete_url = reverse(
            "admin:zaken_zaakinformatieobject_delete", args=(zaakinformatieobject.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(ZaakInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["beschrijving"], "description")
