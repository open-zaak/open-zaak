# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.documenten.models import Gebruiksrechten
from openzaak.utils.tests import AdminTestMixin

from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory
from ..utils import get_operation_url


class GebruiksrechtenAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_gebruiksrechten(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=informatieobject.uuid
        )
        add_url = reverse("admin:documenten_gebruiksrechten_add")
        data = {
            "uuid": uuid.uuid4(),
            "informatieobject": informatieobject.canonical.id,
            "omschrijving_voorwaarden": "desc",
            "startdatum_0": date(2019, 1, 1),
            "startdatum_1": time(10, 0, 0),
        }

        self.client.post(add_url, data)

        self.assertEqual(Gebruiksrechten.objects.count(), 1)

        gebruiksrechten = Gebruiksrechten.objects.get()
        gebruiksrechten_url = get_operation_url(
            "gebruiksrechten_read", uuid=gebruiksrechten.uuid
        )

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "gebruiksrechten"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{gebruiksrechten_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, gebruiksrechten.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["omschrijving_voorwaarden"], "desc")

    def test_change_gebruiksrechten(self):
        gebruiksrechten = GebruiksrechtenFactory.create(omschrijving_voorwaarden="old")
        gebruiksrechten_url = get_operation_url(
            "gebruiksrechten_read", uuid=gebruiksrechten.uuid
        )
        informatieobject = gebruiksrechten.informatieobject
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read",
            uuid=informatieobject.latest_version.uuid,
        )
        change_url = reverse(
            "admin:documenten_gebruiksrechten_change", args=(gebruiksrechten.pk,)
        )
        data = {
            "uuid": gebruiksrechten.uuid,
            "informatieobject": informatieobject.id,
            "omschrijving_voorwaarden": "new",
            "startdatum_0": date(2019, 1, 1),
            "startdatum_1": time(10, 0, 0),
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        gebruiksrechten.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "gebruiksrechten"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{gebruiksrechten_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, gebruiksrechten.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["omschrijving_voorwaarden"], "old")
        self.assertEqual(new_data["omschrijving_voorwaarden"], "new")

    def test_delete_gebruiksrechten_action(self):
        gebruiksrechten = GebruiksrechtenFactory.create(omschrijving_voorwaarden="desc")
        gebruiksrechten_url = get_operation_url(
            "gebruiksrechten_read", uuid=gebruiksrechten.uuid
        )
        informatieobject = gebruiksrechten.informatieobject
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read",
            uuid=informatieobject.latest_version.uuid,
        )
        change_list_url = reverse("admin:documenten_gebruiksrechten_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [gebruiksrechten.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Gebruiksrechten.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "gebruiksrechten"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{gebruiksrechten_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, gebruiksrechten.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["omschrijving_voorwaarden"], "desc")

    def test_delete_gebruiksrechten(self):
        gebruiksrechten = GebruiksrechtenFactory.create(omschrijving_voorwaarden="desc")
        gebruiksrechten_url = get_operation_url(
            "gebruiksrechten_read", uuid=gebruiksrechten.uuid
        )
        informatieobject = gebruiksrechten.informatieobject
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read",
            uuid=informatieobject.latest_version.uuid,
        )
        delete_url = reverse(
            "admin:documenten_gebruiksrechten_delete", args=(gebruiksrechten.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Gebruiksrechten.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "gebruiksrechten"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{gebruiksrechten_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, gebruiksrechten.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["omschrijving_voorwaarden"], "desc")
