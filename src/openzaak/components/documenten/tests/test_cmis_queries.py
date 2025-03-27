# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from openzaak.tests.utils import APICMISTestCase, require_cmis

from ..models import EnkelvoudigInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True, SITE_DOMAIN="testserver")
class QueryTests(APICMISTestCase):
    """
    Test that the query interface works with CMIS as backend.
    """

    def test_filter(self):
        EnkelvoudigInformatieObjectFactory.create(identificatie="001")
        eio2 = EnkelvoudigInformatieObjectFactory.create(identificatie="002")

        eios = EnkelvoudigInformatieObject.objects.filter(identificatie="002")

        self.assertEqual(
            [eio.identificatie for eio in eios],
            [eio2.identificatie],
        )

    def test_filter_then_all(self):
        EnkelvoudigInformatieObjectFactory.create(identificatie="001")
        eio2 = EnkelvoudigInformatieObjectFactory.create(identificatie="002")

        eios = EnkelvoudigInformatieObject.objects.filter(identificatie="002").all()

        self.assertEqual(
            [eio.identificatie for eio in eios],
            [eio2.identificatie],
        )

    def test_chained_filter(self):
        EnkelvoudigInformatieObjectFactory.create(identificatie="001")
        EnkelvoudigInformatieObjectFactory.create(identificatie="002")

        eios = EnkelvoudigInformatieObject.objects.filter(identificatie="001").filter(
            identificatie="002"
        )

        self.assertEqual(list(eios), [])

    def test_all(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(identificatie="001")
        eio2 = EnkelvoudigInformatieObjectFactory.create(identificatie="002")

        eios = EnkelvoudigInformatieObject.objects.all()

        self.assertEqual(
            {eio.identificatie for eio in eios},
            {eio1.identificatie, eio2.identificatie},
        )

    def test_multiple_filters(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(identificatie="001")
        eio2 = EnkelvoudigInformatieObjectFactory.create(identificatie="002")

        eios = EnkelvoudigInformatieObject.objects.all()

        first_filter = eios.filter(identificatie="001")

        self.assertEqual(
            [eio.identificatie for eio in first_filter],
            [eio1.identificatie],
        )

        second_filter = eios.filter(identificatie="002")

        self.assertEqual(
            [eio.identificatie for eio in second_filter],
            [eio2.identificatie],
        )
