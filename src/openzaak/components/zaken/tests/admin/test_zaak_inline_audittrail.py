from datetime import datetime
from django.urls import reverse
from django.utils.timezone import make_aware

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.zaken.models import Status
from openzaak.components.catalogi.tests.factories import StatusTypeFactory

from ..factories import ZaakFactory, StatusFactory
from ..utils import get_operation_url

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory


class ZaakAdminInlineTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.zaak = ZaakFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)
        self.zaak_url = get_operation_url("zaak_read", uuid=self.zaak.uuid)
        self.change_url = reverse("admin:zaken_zaak_change", args=(self.zaak.pk,))

    def assertZaakAudittrail(self, audittrail):
        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{self.zaak_url}"),

    def test_status_delete(self):
        status = StatusFactory.create(zaak=self.zaak)
        status_url = get_operation_url("status_read", uuid=status.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form['status_set-0-DELETE'] = True
        form.submit()

        self.assertEqual(Status.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(status.uuid))

    def test_status_change(self):
        status = StatusFactory.create(zaak=self.zaak, datum_status_gezet=make_aware(datetime(2018, 1, 1)))
        status_url = get_operation_url("status_read", uuid=status.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form['status_set-0-datum_status_gezet_0'] = '01-01-2019'
        form.submit()

        status.refresh_from_db()
        self.assertEqual(status.datum_status_gezet, make_aware(datetime(2019, 1, 1)))

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["datum_status_gezet"], "2018-01-01T00:00:00Z")
        self.assertEqual(new_data["datum_status_gezet"], "2019-01-01T00:00:00Z")

    def test_status_add(self):
        statustype = StatusTypeFactory.create(zaaktype=self.zaak.zaaktype)

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form['status_set-0-statustype'] = statustype.id
        form['status_set-0-datum_status_gezet_0'] = '01-01-2019'
        form['status_set-0-datum_status_gezet_1'] = '10:00:00'
        form['status_set-0-statustoelichting'] = 'desc'
        form.submit()

        self.assertEqual(Status.objects.count(), 1)

        status = Status.objects.get()
        status_url = get_operation_url("status_read", uuid=status.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation())
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(status.uuid))

