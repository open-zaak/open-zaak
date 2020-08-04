# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import EigenschapFactory
from openzaak.components.zaken.models import ZaakEigenschap
from openzaak.utils.tests import AdminTestMixin

from ..factories import ZaakEigenschapFactory, ZaakFactory
from ..utils import get_operation_url


class ZaakEigenschapAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_zaakeigenschap(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        eigenschap = EigenschapFactory.create()

        add_url = reverse("admin:zaken_zaakeigenschap_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_eigenschap": eigenschap.id,
            "_naam": "some name",
            "waarde": "test",
        }

        self.client.post(add_url, data)

        self.assertEqual(ZaakEigenschap.objects.count(), 1)

        zaakeigenschap = ZaakEigenschap.objects.get()
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read", uuid=zaakeigenschap.uuid, zaak_uuid=zaak.uuid
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
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["naam"], "some name")

    def test_change_zaakeigenschap(self):
        zaakeigenschap = ZaakEigenschapFactory.create(_naam="old")
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read",
            uuid=zaakeigenschap.uuid,
            zaak_uuid=zaakeigenschap.zaak.uuid,
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakeigenschap.zaak.uuid)
        change_url = reverse(
            "admin:zaken_zaakeigenschap_change", args=(zaakeigenschap.pk,)
        )
        data = {
            "uuid": zaakeigenschap.uuid,
            "zaak": zaakeigenschap.zaak.id,
            "_eigenschap": zaakeigenschap.eigenschap.id,
            "_naam": "new",
            "waarde": "test",
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaakeigenschap.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["naam"], "old")
        self.assertEqual(new_data["naam"], "new")

    def test_delete_zaakeigenschap_action(self):
        zaakeigenschap = ZaakEigenschapFactory.create(_naam="some name")
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read",
            uuid=zaakeigenschap.uuid,
            zaak_uuid=zaakeigenschap.zaak.uuid,
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakeigenschap.zaak.uuid)
        change_list_url = reverse("admin:zaken_zaakeigenschap_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [zaakeigenschap.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(ZaakEigenschap.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["naam"], "some name")

    def test_delete_zaakeigenschap(self):
        zaakeigenschap = ZaakEigenschapFactory.create(_naam="some name")
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read",
            uuid=zaakeigenschap.uuid,
            zaak_uuid=zaakeigenschap.zaak.uuid,
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaakeigenschap.zaak.uuid)
        delete_url = reverse(
            "admin:zaken_zaakeigenschap_delete", args=(zaakeigenschap.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(ZaakEigenschap.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["naam"], "some name")
