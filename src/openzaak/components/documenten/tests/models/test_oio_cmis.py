from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase, override_settings, tag

import requests_mock
from vng_api_common.tests import reverse

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.utils.query import QueryBlocked
from openzaak.utils.tests import APICMISTestCase

from ...models import ObjectInformatieObject
from ..factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from ..utils import serialise_eio


@tag("oio")
@override_settings(CMIS_ENABLED=True)
class OIOCMISTests(APICMISTestCase):
    def setUp(self) -> None:
        self.eio = EnkelvoudigInformatieObjectFactory.create()
        self.eio_url = f"http://openzaak.nl{reverse(self.eio)}"
        self.eio_response = serialise_eio(self.eio, self.eio_url)

        return super().setUp()

    def test_not_both_zaak_besluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create()

        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(
                informatieobject=self.eio_url, zaak=zaak, besluit=besluit
            )

    def test_either_zaak_or_besluit_required(self):
        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(informatieobject=self.eio_url)

    def test_zio_creates_oio(self):
        self.adapter.register_uri("GET", self.eio_url, json=self.eio_response)
        zio = ZaakInformatieObjectFactory.create(informatieobject=self.eio_url)
        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(
            oio.get_informatieobject_url(), zio.informatieobject._initial_data["url"],
        )
        self.assertEqual(oio.object, zio.zaak)

    def test_bio_creates_oio(self):
        self.adapter.register_uri("GET", self.eio_url, json=self.eio_response)
        bio = BesluitInformatieObjectFactory.create(informatieobject=self.eio_url)

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(
            oio.get_informatieobject_url(), bio.informatieobject._initial_data["url"],
        )
        self.assertEqual(oio.object, bio.besluit)

    def test_zio_delete_oio(self):
        self.adapter.register_uri("GET", self.eio_url, json=self.eio_response)
        zio = ZaakInformatieObjectFactory.create(informatieobject=self.eio_url)

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        zio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)

    def test_bio_delete_oio(self):
        self.adapter.register_uri("GET", self.eio_url, json=self.eio_response)
        bio = BesluitInformatieObjectFactory.create(informatieobject=self.eio_url)

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        bio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)


@override_settings(CMIS_ENABLED=True)
class BlockChangeTestCase(APICMISTestCase):
    def setUp(self) -> None:
        super().setUp()

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://openzaak.nl{reverse(eio)}"
        eio_response = serialise_eio(eio, eio_url)

        self.adapter.register_uri("GET", eio_url, json=eio_response)
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        self.oio = ObjectInformatieObject.objects.get()

    def test_update(self):
        self.assertRaises(
            QueryBlocked, ObjectInformatieObject.objects.update, object_type="besluit"
        )

    def test_delete(self):
        self.assertRaises(QueryBlocked, ObjectInformatieObject.objects.all().delete)

    def test_bulk_update(self):
        self.oio.object_type = "besluit"
        self.assertRaises(
            QueryBlocked,
            ObjectInformatieObject.objects.bulk_update,
            [self.oio],
            fields=["object_type"],
        )

    def test_bulk_create(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()
        zaak = ZaakFactory.create()
        oio = ObjectInformatieObject(
            informatieobject=canonical, zaak=zaak, object_type="zaak"
        )

        self.assertRaises(
            QueryBlocked, ObjectInformatieObject.objects.bulk_create, [oio]
        )
