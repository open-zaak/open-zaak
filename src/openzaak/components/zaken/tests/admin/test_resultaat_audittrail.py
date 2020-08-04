# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import ResultaatTypeFactory
from openzaak.components.zaken.models import Resultaat
from openzaak.utils.tests import AdminTestMixin

from ..factories import ResultaatFactory, ZaakFactory
from ..utils import get_operation_url


class ResultaatAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_resultaat(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create()

        add_url = reverse("admin:zaken_resultaat_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_resultaattype": resultaattype.id,
            "toelichting": "desc",
        }

        self.client.post(add_url, data)

        self.assertEqual(Resultaat.objects.count(), 1)

        resultaat = Resultaat.objects.get()
        resultaat_url = get_operation_url(
            "resultaat_read", uuid=resultaat.uuid, zaak_uuid=zaak.uuid
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
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data["toelichting"], "desc")

    def test_change_resultaat(self):
        resultaat = ResultaatFactory.create(toelichting="old")
        resultaat_url = get_operation_url(
            "resultaat_read", uuid=resultaat.uuid, zaak_uuid=resultaat.zaak.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=resultaat.zaak.uuid)
        change_url = reverse("admin:zaken_resultaat_change", args=(resultaat.pk,))
        data = {
            "uuid": resultaat.uuid,
            "zaak": resultaat.zaak.id,
            "_resultaattype": resultaat.resultaattype.id,
            "toelichting": "new",
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        resultaat.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

    def test_delete_resultaat_action(self):
        resultaat = ResultaatFactory.create(toelichting="some desc")
        resultaat_url = get_operation_url(
            "resultaat_read", uuid=resultaat.uuid, zaak_uuid=resultaat.zaak.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=resultaat.zaak.uuid)
        change_list_url = reverse("admin:zaken_resultaat_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [resultaat.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Resultaat.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["toelichting"], "some desc")

    def test_delete_resultaat(self):
        resultaat = ResultaatFactory.create(toelichting="some desc")
        resultaat_url = get_operation_url(
            "resultaat_read", uuid=resultaat.uuid, zaak_uuid=resultaat.zaak.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=resultaat.zaak.uuid)
        delete_url = reverse("admin:zaken_resultaat_delete", args=(resultaat.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Resultaat.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data["toelichting"], "some desc")
