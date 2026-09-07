# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse as django_reverse

from maykin_2fa.test import disable_admin_mfa
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.besluiten.api.audits import AUDIT_BRC
from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.api.audits import AUDIT_ZRC
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import AdminTestMixin
from openzaak.utils.urls import reverse


@disable_admin_mfa()
class BesluitInformatieObjectAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_create_bio(self):
        besluit = BesluitFactory.create()
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        add_url = django_reverse("admin:besluiten_besluitinformatieobject_add")
        data = {
            "uuid": uuid.uuid4(),
            "besluit": besluit.id,
            "_informatieobject": informatieobject.canonical.id,
        }

        self.client.post(add_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        bio = BesluitInformatieObject.objects.get()

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )

    def test_create_bio_with_zaak(self):
        besluit = BesluitFactory.create(for_zaak=True)
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        add_url = django_reverse("admin:besluiten_besluitinformatieobject_add")
        data = {
            "uuid": uuid.uuid4(),
            "besluit": besluit.id,
            "_informatieobject": informatieobject.canonical.id,
        }

        self.client.post(add_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        bio = BesluitInformatieObject.objects.get()

        self.assertEqual(AuditTrail.objects.count(), 2)

        brc_audittrail = AuditTrail.objects.get(bron=AUDIT_BRC.component_name)
        self.assertEqual(brc_audittrail.actie, "create")
        self.assertEqual(brc_audittrail.resultaat, 0)
        self.assertEqual(brc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(brc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(brc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            brc_audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            brc_audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(brc_audittrail.oud, None)

        new_data = brc_audittrail.nieuw
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )

        zrc_audittrail = AuditTrail.objects.get(bron=AUDIT_ZRC.component_name)
        self.assertEqual(zrc_audittrail.actie, "create")
        self.assertEqual(zrc_audittrail.resultaat, 0)
        self.assertEqual(zrc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(zrc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(zrc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            zrc_audittrail.hoofd_object,
            f"http://testserver{reverse(besluit.zaak, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            zrc_audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(zrc_audittrail.oud, None)

        new_data = zrc_audittrail.nieuw
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit, namespace='zaken')}",
        )

    def test_change_bio(self):
        besluit_old, besluit_new = BesluitFactory.create_batch(2)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit_old)
        change_url = django_reverse(
            "admin:besluiten_besluitinformatieobject_change", args=(bio.pk,)
        )
        data = {
            "uuid": bio.uuid,
            "besluit": besluit_new.id,
            "_informatieobject": bio.informatieobject.id,
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        bio.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit_new, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())

        old_data, new_data = audittrail.oud, audittrail.nieuw

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(besluit_old, namespace='besluiten')}",
        )
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit_new, namespace='besluiten')}",
        )

    def test_change_bio_with_zaak(self):
        besluit_old, besluit_new = BesluitFactory.create_batch(2)
        besluit_new.zaak = ZaakFactory.create()
        besluit_new.save()

        bio = BesluitInformatieObjectFactory.create(besluit=besluit_old)
        change_url = django_reverse(
            "admin:besluiten_besluitinformatieobject_change", args=(bio.pk,)
        )
        data = {
            "uuid": bio.uuid,
            "besluit": besluit_new.id,
            "_informatieobject": bio.informatieobject.id,
        }

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 2)

        bio.refresh_from_db()

        audittrail = AuditTrail.objects.get(bron=AUDIT_BRC.component_name)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit_new, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())

        old_data, new_data = audittrail.oud, audittrail.nieuw

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(besluit_old, namespace='besluiten')}",
        )
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit_new, namespace='besluiten')}",
        )

        audittrail = AuditTrail.objects.get(bron=AUDIT_ZRC.component_name)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit_new.zaak, namespace='zaken')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='zaken')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())

        old_data, new_data = audittrail.oud, audittrail.nieuw

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(besluit_old, namespace='zaken')}",
        )
        self.assertEqual(
            new_data["besluit"],
            f"http://testserver{reverse(besluit_new, namespace='zaken')}",
        )

    def test_delete_bio_action(self):
        bio = BesluitInformatieObjectFactory.create()
        change_list_url = django_reverse(
            "admin:besluiten_besluitinformatieobject_changelist"
        )
        data = {
            "action": "delete_selected",
            "_selected_action": [bio.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )

    def test_delete_bio(self):
        bio = BesluitInformatieObjectFactory.create()
        delete_url = django_reverse(
            "admin:besluiten_besluitinformatieobject_delete", args=(bio.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )

    def test_delete_bio_with_zaak(self):
        bio = BesluitInformatieObjectFactory.create()
        bio.besluit.zaak = ZaakFactory.create()
        bio.besluit.save()

        delete_url = django_reverse(
            "admin:besluiten_besluitinformatieobject_delete", args=(bio.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 2)

        brc_audittrail = AuditTrail.objects.get(bron=AUDIT_BRC.component_name)
        self.assertEqual(brc_audittrail.actie, "destroy")
        self.assertEqual(brc_audittrail.resultaat, 0)
        self.assertEqual(brc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(brc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(brc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            brc_audittrail.hoofd_object,
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            brc_audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(brc_audittrail.nieuw, None)

        old_data = brc_audittrail.oud

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(bio.besluit, namespace='besluiten')}",
        )

        zrc_audittrail = AuditTrail.objects.get(bron=AUDIT_ZRC.component_name)
        self.assertEqual(zrc_audittrail.actie, "destroy")
        self.assertEqual(zrc_audittrail.resultaat, 0)
        self.assertEqual(zrc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(zrc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(zrc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            zrc_audittrail.hoofd_object,
            f"http://testserver{reverse(bio.besluit.zaak, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource, "besluitinformatieobject")
        self.assertEqual(
            zrc_audittrail.resource_url,
            f"http://testserver{reverse(bio, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(zrc_audittrail.nieuw, None)

        old_data = zrc_audittrail.oud

        self.assertEqual(
            old_data["besluit"],
            f"http://testserver{reverse(bio.besluit, namespace='zaken')}",
        )
