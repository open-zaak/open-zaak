# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.test import APITestCase

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)

from ..factories import RolFactory, ZaakInformatieObjectFactory


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

    def test_rol_unique_repr_does_not_exceed_200_chars(self):
        rol = RolFactory.build(
            zaak__identificatie="foo", roltoelichting="a" * 200, betrokkene="",
        )

        unique_repr = rol.unique_representation()

        self.assertLessEqual(len(unique_repr), 200)
