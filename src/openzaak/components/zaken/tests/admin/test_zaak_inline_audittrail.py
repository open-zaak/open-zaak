from datetime import datetime
from django.urls import reverse
from django.utils.timezone import make_aware

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.zaken.models import Status

from ..factories import ZaakFactory, StatusFactory
from ..utils import get_operation_url

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory


class ZaakAdminInlineTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_inline(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        status = StatusFactory.create(zaak=zaak)
        status_url = get_operation_url("status_read", uuid=status.uuid)
        change_url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        get_response = self.app.get(change_url)

        form = get_response.form
        form['status_set-0-DELETE'] = True
        form.submit()

        # print(get_response)
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

        self.assertEqual(old_data["uuid"], str(status.uuid))

    def test_change_inline(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        status = StatusFactory.create(zaak=zaak, datum_status_gezet=make_aware(datetime(2018, 1, 1)))
        status_url = get_operation_url("status_read", uuid=status.uuid)
        change_url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        get_response = self.app.get(change_url)

        form = get_response.form
        form['status_set-0-datum_status_gezet_0'] = '01-01-2019'
        form.submit()

        status.refresh_from_db()
        self.assertEqual(status.datum_status_gezet, make_aware(datetime(2019, 1, 1)))

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
        self.assertEqual(old_data["datum_status_gezet"], "2018-01-01T00:00:00Z")
        self.assertEqual(new_data["datum_status_gezet"], "2019-01-01T00:00:00Z")

    def test_add_inline(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        change_url = reverse("admin:zaken_zaak_change", args=(zaak.pk,))

        get_response = self.app.get(change_url)
        form = get_response.form

        form['status_set-0-datum_status_gezet_0'] = '01-01-2019'
        form.submit()

