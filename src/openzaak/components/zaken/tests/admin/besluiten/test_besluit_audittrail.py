# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from typing import Type

from django.test import TestCase
from django.urls import reverse as django_reverse

from maykin_2fa.test import disable_admin_mfa
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.besluiten.models import Besluit
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.zaken.models import Zaak
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import AdminTestMixin
from openzaak.utils.urls import reverse

inline_data = {
    "besluitinformatieobject_set-TOTAL_FORMS": 0,
    "besluitinformatieobject_set-INITIAL_FORMS": 0,
    "besluitinformatieobject_set-MIN_NUM_FORMS": 0,
    "besluitinformatieobject_set-MAX_NUM_FORMS": 1000,
}


@disable_admin_mfa()
class BesluitAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def _create_besluit(self, zaak: Type[Zaak] | None = None):
        besluittype = BesluitTypeFactory.create(concept=False)
        add_url = django_reverse("admin:besluiten_besluit_add")
        data = {
            "uuid": uuid.uuid4(),
            "besluittype": besluittype.id,
            "verantwoordelijke_organisatie": "517439943",
            "datum": "15-11-2019",
            "ingangsdatum": "15-11-2019",
            "toelichting": "desc",
        }
        data.update(inline_data)

        if zaak:
            data.update(
                {
                    "_zaak": zaak.id,
                }
            )

        self.client.post(add_url, data)

        self.assertEqual(Besluit.objects.count(), 1)

        return Besluit.objects.get()

    def test_create_besluit(self):
        besluit = self._create_besluit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluit")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, besluit.unique_representation())

        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["toelichting"], "desc")

    def test_create_besluit_with_zaak(self):
        zaak = ZaakFactory.create()
        besluit = self._create_besluit(zaak)

        self.assertEqual(AuditTrail.objects.count(), 2)

        brc_audittrail = AuditTrail.objects.get(bron="BRC")
        self.assertEqual(brc_audittrail.actie, "create")
        self.assertEqual(brc_audittrail.resultaat, 0)
        self.assertEqual(brc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(brc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(brc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            brc_audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource, "besluit")
        self.assertEqual(
            brc_audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(
            brc_audittrail.resource_weergave, besluit.unique_representation()
        )

        self.assertEqual(brc_audittrail.oud, None)

        new_data = brc_audittrail.nieuw
        self.assertEqual(new_data["toelichting"], "desc")

        zrc_audittrail = AuditTrail.objects.get(bron="ZRC")
        self.assertEqual(zrc_audittrail.actie, "create")
        self.assertEqual(zrc_audittrail.resultaat, 0)
        self.assertEqual(zrc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(zrc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(zrc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            zrc_audittrail.hoofd_object,
            f"http://testserver{reverse(zaak, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource, "besluit")
        self.assertEqual(
            zrc_audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='zaken')}",
        )
        self.assertEqual(
            zrc_audittrail.resource_weergave, besluit.unique_representation()
        )

        self.assertEqual(zrc_audittrail.oud, None)

        new_data = zrc_audittrail.nieuw
        self.assertEqual(new_data["toelichting"], "desc")

    def test_change_besluit(self):
        besluit = BesluitFactory.create(toelichting="old")
        change_url = django_reverse(
            "admin:besluiten_besluit_change", args=(besluit.pk,)
        )
        data = {
            "uuid": besluit.uuid,
            "besluittype": besluit.besluittype.id,
            "verantwoordelijke_organisatie": besluit.verantwoordelijke_organisatie,
            "datum": besluit.datum,
            "ingangsdatum": "15-11-2019",
            "toelichting": "new",
        }
        data.update(inline_data)

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        besluit.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource, "besluit")
        self.assertEqual(
            audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(audittrail.resource_weergave, besluit.unique_representation())

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

    def test_change_besluit_add_zaak(self):
        besluit = BesluitFactory.create(toelichting="old")
        zaak = ZaakFactory.create()
        change_url = django_reverse(
            "admin:besluiten_besluit_change", args=(besluit.pk,)
        )
        data = {
            "uuid": besluit.uuid,
            "_besluittype": besluit._besluittype.id,
            "verantwoordelijke_organisatie": besluit.verantwoordelijke_organisatie,
            "datum": besluit.datum,
            "ingangsdatum": "15-11-2019",
            "toelichting": "new",
            "_zaak": zaak.id,
        }
        data.update(inline_data)

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 2)

        besluit.refresh_from_db()

        brc_audittrail = AuditTrail.objects.get(bron="BRC")
        self.assertEqual(brc_audittrail.actie, "update")
        self.assertEqual(brc_audittrail.resultaat, 0)
        self.assertEqual(brc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(brc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(brc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            brc_audittrail.hoofd_object,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(brc_audittrail.resource, "besluit")
        self.assertEqual(
            brc_audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )
        self.assertEqual(
            brc_audittrail.resource_weergave, besluit.unique_representation()
        )

        old_data, new_data = brc_audittrail.oud, brc_audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

        zrc_audittrail = AuditTrail.objects.get(bron="ZRC")
        self.assertEqual(zrc_audittrail.actie, "update")
        self.assertEqual(zrc_audittrail.resultaat, 0)
        self.assertEqual(zrc_audittrail.applicatie_weergave, "admin")
        self.assertEqual(zrc_audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(zrc_audittrail.gebruikers_weergave, self.user.get_full_name())
        self.assertEqual(
            zrc_audittrail.hoofd_object,
            f"http://testserver{reverse(zaak, namespace='zaken')}",
        )
        self.assertEqual(zrc_audittrail.resource, "besluit")
        self.assertEqual(
            zrc_audittrail.resource_url,
            f"http://testserver{reverse(besluit, namespace='zaken')}",
        )
        self.assertEqual(
            zrc_audittrail.resource_weergave, besluit.unique_representation()
        )

        old_data, new_data = zrc_audittrail.oud, zrc_audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

    def test_delete_besluit_action(self):
        besluit = self._create_besluit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        change_list_url = django_reverse("admin:besluiten_besluit_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [besluit.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(Besluit.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_delete_besluit(self):
        besluit = self._create_besluit()

        self.assertEqual(AuditTrail.objects.count(), 1)

        delete_url = django_reverse(
            "admin:besluiten_besluit_delete", args=(besluit.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Besluit.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_delete_besluit_with_zaak(self):
        zaak = ZaakFactory.create()
        besluit = self._create_besluit(zaak)

        delete_url = django_reverse(
            "admin:besluiten_besluit_delete", args=(besluit.pk,)
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(Besluit.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 2)

        zrc_delete_trail = AuditTrail.objects.get(actie="destroy")
        self.assertEqual(zrc_delete_trail.bron, "ZRC")
        self.assertEqual(
            zrc_delete_trail.hoofd_object,
            f"http://testserver{reverse(zaak, namespace='zaken')}",
        )
