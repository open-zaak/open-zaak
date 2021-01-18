# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase

from ..factories import StatusTypeFactory, ZaakTypeFactory


class StatustypeTests(TestCase):
    def test_fill_in_default_archiefnominatie(self):
        """
        Assert that the is_eindstatus is calculated correctly
        """
        zaaktype = ZaakTypeFactory.create()
        statustype1 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype2 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype3 = StatusTypeFactory.create(zaaktype=zaaktype)

        self.assertEqual(statustype1.is_eindstatus(), False)
        self.assertEqual(statustype2.is_eindstatus(), False)
        self.assertEqual(statustype3.is_eindstatus(), True)
