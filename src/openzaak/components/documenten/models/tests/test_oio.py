from django.db import IntegrityError
from django.test import TestCase, tag

from openzaak.components.besluiten.models.tests.factories import (
    BesluitFactory, BesluitInformatieObjectFactory
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory
)
from openzaak.components.zaken.models.tests.factories import (
    ZaakFactory, ZaakInformatieObjectFactory
)

from ..models import ObjectInformatieObject


@tag("oio")
class OIOTests(TestCase):

    def test_not_both_zaak_besluit(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create()

        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(
                informatieobject=canonical,
                zaak=zaak,
                besluit=besluit,
            )

    def test_either_zaak_or_besluit_required(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()

        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(informatieobject=canonical, zaak=None, besluit=None)

    def test_zio_creates_oio(self):
        zio = ZaakInformatieObjectFactory.create()

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(oio.informatieobject, zio.informatieobject)
        self.assertEqual(oio.object, zio.zaak)

    def test_bio_creates_oio(self):
        bio = BesluitInformatieObjectFactory.create()

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(oio.informatieobject, bio.informatieobject)
        self.assertEqual(oio.object, bio.besluit)

    def test_zio_delete_oio(self):
        bio = BesluitInformatieObjectFactory.create()

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        bio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)

    def test_bio_delete_oio(self):
        bio = BesluitInformatieObjectFactory.create()

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        bio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)
