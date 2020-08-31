# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import TestCase

from ..factories import EnkelvoudigInformatieObjectFactory


class EIOTests(TestCase):
    def test_default_human_readable(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie="", creatiedatum=date(2019, 7, 1)
        )

        self.assertEqual(eio.identificatie, "DOCUMENT-2019-0000000001")

    def test_default_human_readable_existing_data(self):
        EnkelvoudigInformatieObjectFactory.create(
            creatiedatum=date(2019, 7, 1), identificatie="DOCUMENT-2019-0000000015"
        )

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            identificatie="", creatiedatum=date(2019, 9, 15)
        )

        self.assertEqual(eio2.identificatie, "DOCUMENT-2019-0000000016")
