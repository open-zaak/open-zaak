import uuid

from datetime import date, time
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from openzaak.components.zaken.models import Zaak
from ..factories import ZaakFactory, StatusFactory
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from vng_api_common.audittrails.models import AuditTrail
from openzaak.utils.tests import AdminTestMixin
from ..utils import get_operation_url


inline_data = {
    "status_set-TOTAL_FORMS": 3,
    "status_set-INITIAL_FORMS": 0,
    "status_set-MIN_NUM_FORMS": 0,
    "status_set-MAX_NUM_FORMS": 1000,
    "zaakobject_set-TOTAL_FORMS": 3,
    "zaakobject_set-INITIAL_FORMS": 0,
    "zaakobject_set-MIN_NUM_FORMS": 0,
    "zaakobject_set-MAX_NUM_FORMS": 1000,
    "zaakinformatieobject_set-TOTAL_FORMS": 3,
    "zaakinformatieobject_set-INITIAL_FORMS": 0,
    "zaakinformatieobject_set-MIN_NUM_FORMS": 0,
    "zaakinformatieobject_set-MAX_NUM_FORMS": 1000,
    "klantcontact_set-TOTAL_FORMS": 3,
    "klantcontact_set-INITIAL_FORMS": 0,
    "klantcontact_set-MIN_NUM_FORMS": 0,
    "klantcontact_set-MAX_NUM_FORMS": 1000,
    "zaakeigenschap_set-TOTAL_FORMS": 3,
    "zaakeigenschap_set-INITIAL_FORMS": 0,
    "zaakeigenschap_set-MIN_NUM_FORMS": 0,
    "zaakeigenschap_set-MAX_NUM_FORMS": 1000,
    "rol_set-TOTAL_FORMS": 3,
    "rol_set-INITIAL_FORMS": 0,
    "rol_set-MIN_NUM_FORMS": 0,
    "rol_set-MAX_NUM_FORMS": 1000,
    "resultaat-TOTAL_FORMS": 1,
    "resultaat-INITIAL_FORMS": 0,
    "resultaat-MIN_NUM_FORMS": 0,
    "resultaat-MAX_NUM_FORMS": 1,
    "relevante_andere_zaken-TOTAL_FORMS": 3,
    "relevante_andere_zaken-INITIAL_FORMS": 0,
    "relevante_andere_zaken-MIN_NUM_FORMS": 0,
    "relevante_andere_zaken-MAX_NUM_FORMS": 1000
}


class ZaakAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        add_url = reverse('admin:zaken_zaak_add')
        data = {
            "uuid": uuid.uuid4(),
            "zaaktype": zaaktype.id,
            "bronorganisatie": "517439943",
            "registratiedatum": "15-11-2019",
            "verantwoordelijke_organisatie": "517439943",
            "startdatum": "15-11-2019",
            "vertrouwelijkheidaanduiding": "openbaar",
            "archiefstatus": "nog_te_archiveren"
        }
        data.update(inline_data)

        self.client.post(add_url, data)

        self.assertEqual(Zaak.objects.count(), 1)

        zaak = Zaak.objects.get()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaak'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data['verantwoordelijke_organisatie'], '517439943')

    def test_change_zaak(self):
        zaak = ZaakFactory.create(vertrouwelijkheidaanduiding='intern')
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        change_url = reverse('admin:zaken_zaak_change', args=(zaak.pk,))
        data = {
            "uuid": zaak.uuid,
            "zaaktype": zaak.zaaktype.id,
            "bronorganisatie": "517439943",
            "registratiedatum": "15-11-2019",
            "verantwoordelijke_organisatie": "517439943",
            "startdatum": "15-11-2019",
            "vertrouwelijkheidaanduiding": "openbaar",
            "archiefstatus": "nog_te_archiveren"
        }
        data.update(inline_data)

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaak.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaak'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data['vertrouwelijkheidaanduiding'], 'intern')
        self.assertEqual(new_data['vertrouwelijkheidaanduiding'], 'openbaar')

    def test_delete_zaak_action(self):
        zaak = ZaakFactory.create(vertrouwelijkheidaanduiding='intern')
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        change_list_url = reverse('admin:zaken_zaak_changelist')
        data = {'action': 'delete_selected', '_selected_action': [zaak.id], 'post': 'yes'}

        self.client.post(change_list_url, data)

        self.assertEqual(Zaak.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaak'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['vertrouwelijkheidaanduiding'], 'intern')

    def test_delete_zaak(self):
        zaak = ZaakFactory.create(vertrouwelijkheidaanduiding='intern')
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        delete_url = reverse('admin:zaken_zaak_delete', args=(zaak.pk,))
        data = {'post': 'yes'}

        self.client.post(delete_url, data)

        self.assertEqual(Zaak.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaak'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource_weergave, zaak.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['vertrouwelijkheidaanduiding'], 'intern')
