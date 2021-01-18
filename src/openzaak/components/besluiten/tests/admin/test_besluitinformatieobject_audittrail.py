# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import AdminTestMixin

from ..factories import BesluitFactory, BesluitInformatieObjectFactory
from ..utils import get_operation_url


class BesluitInformatieObjectAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_bio(self):
        besluit = BesluitFactory.create()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        add_url = reverse("admin:besluiten_besluitinformatieobject_add")
        data = {
            "uuid": uuid.uuid4(),
            "besluit": besluit.id,
            "_informatieobject": informatieobject.canonical.id,
        }

        self.client.post(add_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        bio = BesluitInformatieObject.objects.get()
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["besluit"], f"http://testserver{besluit_url}")

    def test_change_bio(self):
        besluit_old, besluit_new = BesluitFactory.create_batch(2)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit_old)
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)
        change_url = reverse(
            "admin:besluiten_besluitinformatieobject_change", args=(bio.pk,)
        )
        data = {
            "uuid": bio.uuid,
            "besluit": besluit_new.id,
            "_informatieobject": bio.informatieobject.id,
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        bio.refresh_from_db()
        audittrail = AuditTrail.objects.get()
        besluit_old_url = get_operation_url("besluit_read", uuid=besluit_old.uuid)
        besluit_new_url = get_operation_url("besluit_read", uuid=besluit_new.uuid)

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{besluit_new_url}"
        ),
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw

        self.assertEqual(old_data["besluit"], f"http://testserver{besluit_old_url}")
        self.assertEqual(new_data["besluit"], f"http://testserver{besluit_new_url}")

    def test_delete_bio_action(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)
        besluit_url = get_operation_url("besluit_read", uuid=bio.besluit.uuid)
        change_list_url = reverse("admin:besluiten_besluitinformatieobject_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [bio.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["besluit"], f"http://testserver{besluit_url}")

    def test_delete_bio(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)
        besluit_url = get_operation_url("besluit_read", uuid=bio.besluit.uuid)
        delete_url = reverse(
            "admin:besluiten_besluitinformatieobject_delete", args=(bio.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}"),
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["besluit"], f"http://testserver{besluit_url}")
