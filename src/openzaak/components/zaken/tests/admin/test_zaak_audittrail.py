# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.zaken.models import Zaak
from openzaak.utils.tests import AdminTestMixin

from ..factories import ZaakFactory
from ..utils import get_operation_url


class ZaakAdminTests(AdminTestMixin, WebTest):
    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def _create_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        add_url = reverse("admin:zaken_zaak_add")
        data = {
            "_zaaktype": zaaktype.id,
            "bronorganisatie": "517439943",
            "registratiedatum": "15-11-2019",
            "verantwoordelijke_organisatie": "517439943",
            "startdatum": "15-11-2019",
            "vertrouwelijkheidaanduiding": "openbaar",
            "archiefstatus": "nog_te_archiveren",
        }

        add_page = self.app.get(add_url)
        for field, value in data.items():
            add_page.form[field] = value

        add_page.form.submit().follow()
        self.assertEqual(Zaak.objects.count(), 1)
        return Zaak.objects.get()

    def test_create_zaak(self):
        zaak = self._create_zaak()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaak"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["verantwoordelijke_organisatie"], "517439943")

    def test_change_zaak(self):
        zaak = ZaakFactory.create(vertrouwelijkheidaanduiding="intern")
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        change_url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))
        data = {
            "_zaaktype": zaak.zaaktype.id,
            "bronorganisatie": "517439943",
            "registratiedatum": "15-11-2019",
            "verantwoordelijke_organisatie": "517439943",
            "startdatum": "15-11-2019",
            "vertrouwelijkheidaanduiding": "openbaar",
            "archiefstatus": "nog_te_archiveren",
        }
        change_page = self.app.get(change_url)
        for field, value in data.items():
            change_page.form[field] = value

        change_page.form.submit().follow()

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaak.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource, "zaak"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaak_url}"),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["vertrouwelijkheidaanduiding"], "intern")
        self.assertEqual(new_data["vertrouwelijkheidaanduiding"], "openbaar")

    def test_delete_zaak_action(self):
        zaak = self._create_zaak()

        self.assertEqual(AuditTrail.objects.count(), 1)

        change_list_url = reverse("admin:zaken_zaak_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [zaak.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Zaak.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_delete_zaak(self):
        zaak = self._create_zaak()

        self.assertEqual(AuditTrail.objects.count(), 1)

        delete_url = reverse("admin:zaken_zaak_delete", args=(zaak.pk,))
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Zaak.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_save_zaak_without_change(self):
        self.app.set_user(self.user)
        zaak = ZaakFactory.create()
        change_url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        get_response = self.app.get(change_url)

        form = get_response.form
        form.submit()

        self.assertEqual(AuditTrail.objects.count(), 0)
