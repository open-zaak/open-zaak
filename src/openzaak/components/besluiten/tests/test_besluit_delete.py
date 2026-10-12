# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.components.zaken.models import Zaak, ZaakBesluit
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


class BesluitDeleteTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(besluit=besluit)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())

    def test_delete_besluit_with_zaak(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        self.assertTrue(ZaakBesluit.objects.filter(zaak=zaak).exists())
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(ZaakBesluit.objects.exists())
        self.assertTrue(Zaak.objects.filter(pk=zaak.pk).exists())

    def test_delete_besluit_with_zaak_and_informatieobject(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        BesluitInformatieObjectFactory.create(besluit=besluit)
        self.assertTrue(ZaakBesluit.objects.filter(zaak=zaak).exists())
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertFalse(ZaakBesluit.objects.exists())
        self.assertTrue(Zaak.objects.filter(pk=zaak.pk).exists())

    def test_delete_besluit_with_zaak_and_multiple_informatieobjecten(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        BesluitInformatieObjectFactory.create_batch(2, besluit=besluit)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertFalse(ZaakBesluit.objects.exists())

    def test_delete_besluit_only_deletes_own_zaakbesluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        other_besluit = BesluitFactory.create(zaak=zaak)
        BesluitInformatieObjectFactory.create(besluit=besluit)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        zaakbesluit = ZaakBesluit.objects.get()
        self.assertEqual(zaakbesluit.zaak, zaak)
        self.assertEqual(zaakbesluit.besluit, other_besluit)

    def test_delete_besluit_with_zaak_updates_zaak_laatst_gemuteerd(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        BesluitInformatieObjectFactory.create(besluit=besluit)
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        Zaak.objects.filter(pk=zaak.pk).update(laatst_gemuteerd=old)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        zaak.refresh_from_db()
        self.assertGreater(zaak.laatst_gemuteerd, old)
