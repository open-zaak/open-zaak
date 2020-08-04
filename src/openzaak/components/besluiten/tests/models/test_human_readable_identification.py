# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import TestCase

from ...tests.factories import BesluitFactory


class BesluitTests(TestCase):
    def test_human_readable_1(self):
        besluit = BesluitFactory.create(identificatie="", datum=date(2019, 7, 1))

        self.assertEqual(besluit.identificatie, "BESLUIT-2019-0000000001")

    def test_human_readable_2(self):
        BesluitFactory.create(
            identificatie="BESLUIT-2019-0000000020", datum=date(2019, 7, 1)
        )
        besluit = BesluitFactory.create(identificatie="", datum=date(2019, 5, 1))

        self.assertEqual(besluit.identificatie, "BESLUIT-2019-0000000021")
