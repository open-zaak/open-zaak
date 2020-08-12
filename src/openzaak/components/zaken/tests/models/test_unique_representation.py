# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.test import APITestCase

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)

from ..factories import ZaakInformatieObjectFactory


class UniqueRepresentationTestCase(APITestCase):
    def test_zaakinformatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        zio = ZaakInformatieObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            informatieobject=eio.canonical,
        )

        self.assertEqual(
            zio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
