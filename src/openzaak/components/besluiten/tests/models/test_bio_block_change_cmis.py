# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid

from django.test import override_settings

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, require_cmis
from openzaak.utils.query import QueryBlocked

from ...models import BesluitInformatieObject
from ..factories import BesluitFactory, BesluitInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class BlockChangeCMISTestCase(APICMISTestCase):
    def setUp(self) -> None:
        super().setUp()
        Service.objects.create(
            api_root="http://testserver/documenten/api/v1/", api_type=APITypes.drc
        )
        Service.objects.create(
            api_root="http://testserver/catalogi/api/v1/", api_type=APITypes.ztc
        )
        Service.objects.create(
            api_root="http://testserver/besluiten/api/v1/", api_type=APITypes.brc
        )
        eio = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        eio_url = eio.get_url()
        self.bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)

    def test_update(self):
        self.assertRaises(
            QueryBlocked, BesluitInformatieObject.objects.update, uuid=uuid.uuid4()
        )
        self.assertTrue(self.adapter.request_history)

    def test_delete(self):
        self.assertRaises(QueryBlocked, BesluitInformatieObject.objects.all().delete)
        self.assertTrue(self.adapter.request_history)

    def test_bulk_update(self):
        self.bio.uuid = uuid.uuid4()
        self.assertRaises(
            QueryBlocked,
            BesluitInformatieObject.objects.bulk_update,
            [self.bio],
            fields=["uuid"],
        )
        self.assertTrue(self.adapter.request_history)

    def test_bulk_create(self):
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        bio = BesluitInformatieObject(
            besluit=besluit, informatieobject=eio_url, uuid=uuid.uuid4()
        )
        self.assertRaises(
            QueryBlocked, BesluitInformatieObject.objects.bulk_create, [bio]
        )
        self.assertTrue(self.adapter.request_history)
