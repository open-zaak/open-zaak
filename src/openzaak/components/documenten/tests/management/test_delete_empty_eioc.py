# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from django.core.management import call_command

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from openzaak.tests.utils import JWTAuthMixin

from ...models import EnkelvoudigInformatieObjectCanonical
from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


class DeleteEmptyEIOCTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_basic(self):

        eioc = EnkelvoudigInformatieObjectCanonicalFactory(latest_version=None)
        zaak = ZaakFactory()
        zio = ZaakInformatieObjectFactory(informatieobject=eioc, zaak=zaak)

        besluit = BesluitFactory()
        bio = BesluitInformatieObjectFactory(informatieobject=eioc, besluit=besluit)

        zio_url = reverse(zio)
        with self.assertRaises(AttributeError):
            self.client.get(zio_url, **ZAAK_WRITE_KWARGS)

        bio_url = reverse(bio)
        with self.assertRaises(AttributeError):
            self.client.get(bio_url)

        response = self.client.get(reverse(besluit))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse(zaak), **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 1)
        self.assertEqual(ZaakInformatieObject.objects.count(), 1)
        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        call_command("delete_empty_eioc")

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)
        self.assertEqual(ZaakInformatieObject.objects.count(), 0)
        self.assertEqual(BesluitInformatieObject.objects.count(), 0)
