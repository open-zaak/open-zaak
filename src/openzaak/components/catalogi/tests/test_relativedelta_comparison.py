# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import operator

from django.test import SimpleTestCase

from dateutil.relativedelta import relativedelta

from ..utils import compare_relativedeltas


class RelativeDeltaComparisonTests(SimpleTestCase):
    def test_years_greater_than_but_equal(self):
        rd1 = relativedelta(years=1)
        rd2 = relativedelta(years=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_years_greater_than_but_smaller(self):
        rd1 = relativedelta(years=1)
        rd2 = relativedelta(years=2)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_years_greater_than(self):
        rd1 = relativedelta(years=2)
        rd2 = relativedelta(years=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertTrue(greater)

    def test_months_greater_than_but_equal(self):
        rd1 = relativedelta(months=1)
        rd2 = relativedelta(months=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_months_greater_than_but_smaller(self):
        rd1 = relativedelta(months=1)
        rd2 = relativedelta(months=2)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_months_greater_than(self):
        rd1 = relativedelta(months=2)
        rd2 = relativedelta(months=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertTrue(greater)

    def test_days_greater_than_but_equal(self):
        rd1 = relativedelta(days=1)
        rd2 = relativedelta(days=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_days_greater_than_but_smaller(self):
        rd1 = relativedelta(days=1)
        rd2 = relativedelta(days=2)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertFalse(greater)

    def test_days_greater_than(self):
        rd1 = relativedelta(days=2)
        rd2 = relativedelta(days=1)

        greater = compare_relativedeltas(rd1, rd2, comparison=operator.gt)

        self.assertTrue(greater)

    def test_combinations_greater_than(self):
        rd1s = (
            {"years": 1, "months": 1},
            {"months": 13},
            {"years": 1, "months": 1, "days": 1},
        )
        rd2s = (
            {"years": 1, "months": 0},
            {"years": 1, "months": 0},
            {"years": 1, "months": 1},
        )

        for _rd1, _rd2 in zip(rd1s, rd2s):
            rd1 = relativedelta(**_rd1)
            rd2 = relativedelta(**_rd2)
            with self.subTest(rd1=rd1, rd2=rd2):
                greater = compare_relativedeltas(rd1, rd2)

                self.assertTrue(greater)

    def test_combinations_less_than(self):
        rd1s = (
            {"years": 1, "months": 1},
            {"years": 0, "months": 13},
            {"years": 1, "months": 1, "days": 1},
        )
        rd2s = (
            {"years": 1, "months": 0},
            {"years": 1, "months": 0},
            {"years": 1, "months": 1},
        )

        for _rd1, _rd2 in zip(rd1s, rd2s):
            rd1 = relativedelta(**_rd1)
            rd2 = relativedelta(**_rd2)
            with self.subTest(rd1=rd1, rd2=rd2):
                less = compare_relativedeltas(rd1, rd2, comparison=operator.lt)

                self.assertFalse(less)

    def test_only_days(self):
        rd1 = relativedelta(days=29)
        rd2 = relativedelta(days=26)

        greater = compare_relativedeltas(rd1, rd2)

        self.assertTrue(greater)
