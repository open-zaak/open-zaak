import uuid

from django.test import TestCase
from django.urls import reverse

from openzaak.components.zaken.models import ZaakObject
from ..factories import ZaakFactory, ZaakObjectFactory
from vng_api_common.audittrails.models import AuditTrail
from openzaak.utils.tests import AdminTestMixin
from ..utils import get_operation_url


class ZaakObjectAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_zaakobject(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        add_url = reverse('admin:zaken_zaakobject_add')
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "object": "http://example.com/adres/1",
            "object_type": "adres",
        }

        self.client.post(add_url, data)

        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaakobject'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaakobject_url}'),
        self.assertEqual(audittrail.resource_weergave, zaakobject.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data['object_type'],  'adres')

    def test_change_zaakobject(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        change_url = reverse('admin:zaken_zaakobject_change', args=(zaakobject.pk,))
        data = {
            "uuid": zaakobject.uuid,
            "zaak": zaakobject.zaak.id,
            "object": "http://example.com/adres/2",
            "object_type": zaakobject.object_type,

        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        zaakobject.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaakobject'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaakobject_url}'),
        self.assertEqual(audittrail.resource_weergave, zaakobject.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data['object'], 'http://example.com/adres/1')
        self.assertEqual(new_data['object'], 'http://example.com/adres/2')

    def test_delete_zaakobject_action(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        change_list_url = reverse('admin:zaken_zaakobject_changelist')
        data = {'action': 'delete_selected', '_selected_action': [zaakobject.id], 'post': 'yes'}

        self.client.post(change_list_url, data)

        self.assertEqual(ZaakObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaakobject'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaakobject_url}'),
        self.assertEqual(audittrail.resource_weergave, zaakobject.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['object'], "http://example.com/adres/1")

    def test_delete_zaakobject(self):
        zaakobject = ZaakObjectFactory.create(object="http://example.com/adres/1")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaakobject.zaak.uuid)
        delete_url = reverse('admin:zaken_zaakobject_delete', args=(zaakobject.pk,))
        data = {'post': 'yes'}

        self.client.post(delete_url, data)

        self.assertEqual(ZaakObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'zaakobject'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{zaakobject_url}'),
        self.assertEqual(audittrail.resource_weergave, zaakobject.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['object'], "http://example.com/adres/1")

