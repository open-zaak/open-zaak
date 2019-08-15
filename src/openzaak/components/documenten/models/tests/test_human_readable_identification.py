from datetime import date

from django.test import TestCase

from ..models import (
    EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical
)
from openzaak.components.catalogi.models.tests.factories import InformatieObjectTypeFactory


class EIOTests(TestCase):

    def test_default_human_readable(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()
        eio = EnkelvoudigInformatieObject.objects.create(
            canonical=canonical,
            creatiedatum=date(2019, 7, 1),
            informatieobjecttype=informatieobjecttype
        )

        self.assertEqual(
            eio.identificatie,
            "DOCUMENT-2019-0000000001"
        )

    def test_default_human_readable_existing_data(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()
        EnkelvoudigInformatieObject.objects.create(
            canonical=canonical,
            creatiedatum=date(2019, 7, 1),
            identificatie="DOCUMENT-2019-0000000015",
            informatieobjecttype=informatieobjecttype
        )

        canonical2 = EnkelvoudigInformatieObjectCanonical.objects.create()
        eio2 = EnkelvoudigInformatieObject.objects.create(
            canonical=canonical2,
            creatiedatum=date(2019, 9, 15),
            informatieobjecttype=informatieobjecttype
        )

        self.assertEqual(
            eio2.identificatie,
            "DOCUMENT-2019-0000000016"
        )
