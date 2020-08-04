# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.besluiten.models import Besluit
from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.utils.tests import AdminTestMixin

from ..factories import BesluitFactory
from ..utils import get_operation_url

inline_data = {
    "besluitinformatieobject_set-TOTAL_FORMS": 0,
    "besluitinformatieobject_set-INITIAL_FORMS": 0,
    "besluitinformatieobject_set-MIN_NUM_FORMS": 0,
    "besluitinformatieobject_set-MAX_NUM_FORMS": 1000,
}


class BesluitAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def _create_besluit(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        add_url = reverse("admin:besluiten_besluit_add")
        data = {
            "uuid": uuid.uuid4(),
            "_besluittype": besluittype.id,
            "verantwoordelijke_organisatie": "517439943",
            "datum": "15-11-2019",
            "ingangsdatum": "15-11-2019",
            "toelichting": "desc",
        }
        data.update(inline_data)

        self.client.post(add_url, data)

        self.assertEqual(Besluit.objects.count(), 1)

        return Besluit.objects.get()

    def test_create_besluit(self):
        besluit = self._create_besluit()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource, "besluit"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource_weergave, besluit.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["toelichting"], "desc")

    def test_change_besluit(self):
        besluit = BesluitFactory.create(toelichting="old")
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        change_url = reverse("admin:besluiten_besluit_change", args=(besluit.pk,))
        data = {
            "uuid": besluit.uuid,
            "_besluittype": besluit._besluittype.id,
            "verantwoordelijke_organisatie": besluit.verantwoordelijke_organisatie,
            "datum": besluit.datum,
            "ingangsdatum": "15-11-2019",
            "toelichting": "new",
        }
        data.update(inline_data)

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        besluit.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource, "besluit"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource_weergave, besluit.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

    def test_delete_besluit_action(self):
        besluit = self._create_besluit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        change_list_url = reverse("admin:besluiten_besluit_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [besluit.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Besluit.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_delete_besluit(self):
        besluit = self._create_besluit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        delete_url = reverse("admin:besluiten_besluit_delete", args=(besluit.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Besluit.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)
