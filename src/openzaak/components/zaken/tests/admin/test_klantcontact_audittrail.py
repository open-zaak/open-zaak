# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.zaken.models import KlantContact
from openzaak.utils.tests import AdminTestMixin

from ..factories import KlantContactFactory, ZaakFactory
from ..utils import get_operation_url


class KlantContactAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_klantcontact(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        add_url = reverse("admin:zaken_klantcontact_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "identificatie": "12345",
            "datumtijd_0": date(2019, 1, 1),
            "datumtijd_1": time(10, 0, 0),
        }

        response = self.client.post(add_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(KlantContact.objects.count(), 1)

        klantcontact = KlantContact.objects.get()
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
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
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["datumtijd"], "2019-01-01T10:00:00Z")

    def test_change_klantcontact(self):
        klantcontact = KlantContactFactory.create(identificatie="123")
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=klantcontact.zaak.uuid)
        change_url = reverse("admin:zaken_klantcontact_change", args=(klantcontact.pk,))
        data = {
            "uuid": klantcontact.uuid,
            "zaak": klantcontact.zaak.id,
            "identificatie": "12345",
            "datumtijd_0": date(2019, 1, 1),
            "datumtijd_1": time(10, 0, 0),
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        klantcontact.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["identificatie"], "123")
        self.assertEqual(new_data["identificatie"], "12345")

    def test_delete_klantcontact_action(self):
        klantcontact = KlantContactFactory.create(identificatie="12345")
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=klantcontact.zaak.uuid)
        change_list_url = reverse("admin:zaken_klantcontact_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [klantcontact.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(KlantContact.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["identificatie"], "12345")

    def test_delete_klantcontact(self):
        klantcontact = KlantContactFactory.create(identificatie="12345")
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=klantcontact.zaak.uuid)
        delete_url = reverse("admin:zaken_klantcontact_delete", args=(klantcontact.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(KlantContact.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["identificatie"], "12345")
