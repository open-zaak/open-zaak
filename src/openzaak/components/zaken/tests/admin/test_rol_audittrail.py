import uuid

from django.test import TestCase
from django.urls import reverse

from openzaak.components.zaken.models import Rol
from openzaak.components.catalogi.tests.factories import RolTypeFactory
from ..factories import ZaakFactory, RolFactory
from vng_api_common.audittrails.models import AuditTrail
from openzaak.utils.tests import AdminTestMixin
from ..utils import get_operation_url


class RolAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_rol(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create()

        add_url = reverse('admin:zaken_rol_add')
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "roltype": roltype.id,
            "betrokkene_type": "natuurlijk_persoon",
            "betrokkene": "http://example.com/betrokkene/1",
            "roltoelichting": "desc",
        }

        response = self.client.post(add_url, data)

        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=zaak.uuid)

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'rol'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{rol_url}'),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw

        self.assertEqual(new_data['roltoelichting'],  'desc')

    def test_change_rol(self):
        rol = RolFactory.create(roltoelichting='old')
        rol_url = get_operation_url("rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        change_url = reverse('admin:zaken_rol_change', args=(rol.pk,))
        data = {
            "uuid": rol.uuid,
            "zaak": rol.zaak.id,
            "roltype": rol.roltype.id,
            "betrokkene_type": rol.betrokkene_type,
            "betrokkene": rol.betrokkene,
            "roltoelichting": "new",
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        rol.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'rol'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{rol_url}'),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data['roltoelichting'], 'old')
        self.assertEqual(new_data['roltoelichting'], 'new')

    def test_delete_rol_action(self):
        rol = RolFactory.create(roltoelichting="some desc")
        rol_url = get_operation_url(
            "rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        change_list_url = reverse('admin:zaken_rol_changelist')
        data = {'action': 'delete_selected', '_selected_action': [rol.id], 'post': 'yes'}

        self.client.post(change_list_url, data)

        self.assertEqual(Rol.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'rol'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{rol_url}'),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['roltoelichting'], "some desc")

    def test_delete_rol(self):
        rol = RolFactory.create(roltoelichting="some desc")
        rol_url = get_operation_url(
            "rol_read", uuid=rol.uuid, zaak_uuid=rol.zaak.uuid
        )
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        delete_url = reverse('admin:zaken_rol_delete', args=(rol.pk,))
        data = {'post': 'yes'}

        self.client.post(delete_url, data)

        self.assertEqual(Rol.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f'{self.user.id}'),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f'http://testserver{zaak_url}'),
        self.assertEqual(audittrail.resource, 'rol'),
        self.assertEqual(audittrail.resource_url, f'http://testserver{rol_url}'),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(old_data['roltoelichting'], "some desc")

