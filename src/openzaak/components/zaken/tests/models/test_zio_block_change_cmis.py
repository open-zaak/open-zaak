# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.query import QueryBlocked
from openzaak.utils.tests import APICMISTestCase, OioMixin, serialise_eio

from ...models import ZaakInformatieObject
from ..factories import ZaakInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class BlockChangeCMISTestCase(APICMISTestCase, OioMixin):
    def setUp(self) -> None:
        super().setUp()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        self.zio = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url, zaak=zaak
        )

    def test_update(self):
        self.assertRaises(
            QueryBlocked, ZaakInformatieObject.objects.update, titel="new"
        )
        self.assertTrue(self.adapter.request_history)

    def test_delete(self):
        self.assertRaises(QueryBlocked, ZaakInformatieObject.objects.all().delete)
        self.assertTrue(self.adapter.request_history)

    def test_bulk_update(self):
        self.zio.title = "new"
        self.assertRaises(
            QueryBlocked,
            ZaakInformatieObject.objects.bulk_update,
            [self.zio],
            fields=["titel"],
        )
        self.assertTrue(self.adapter.request_history)

    def test_bulk_create(self):
        zio = ZaakInformatieObjectFactory.build()
        self.assertRaises(QueryBlocked, ZaakInformatieObject.objects.bulk_create, [zio])
        self.assertTrue(self.adapter.request_history)
