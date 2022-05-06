# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db.models import ProtectedError
from django.test import TestCase

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory

from ..factories import ZaakFactory


class CascadeDeleteTests(TestCase):
    def test_delete_zaaktype_with_zaken_is_blocked(self):
        zt1 = ZaakTypeFactory.create(concept=True)
        zt2 = ZaakTypeFactory.create(concept=True)
        zt3 = ZaakTypeFactory.create(concept=False)
        zt4 = ZaakTypeFactory.create(concept=False)

        ZaakFactory.create(zaaktype=zt1)
        ZaakFactory.create(zaaktype=zt3)

        with self.subTest(concept=True, has_zaken=False):
            zt2.delete()

        with self.subTest(concept=False, has_zaken=False):
            zt4.delete()

        with self.subTest(concept=True, has_zaken=True):
            with self.assertRaises(ProtectedError):
                zt1.delete()

        with self.subTest(concept=False, has_zaken=True):
            with self.assertRaises(ProtectedError):
                zt3.delete()
