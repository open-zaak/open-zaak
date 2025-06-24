# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from datetime import datetime
from unittest.mock import patch

from django.test import TestCase

from openzaak.components.zaken.brondatum import BrondatumCalculator
from openzaak.components.zaken.tests.factories import ResultaatFactory, ZaakFactory


@patch(
    "openzaak.components.catalogi.models.resultaattype.ResultaatType.get_selectielijstklasse",
    return_value={"bewaartermijn": None},
)
class BronDatumTests(TestCase):
    def test_calculate_brondatum_without_archiefactietermijn(
        self, mock_get_selectielijstklasse
    ):
        zaak = ZaakFactory()
        # when archiefactietermijn is not set it is set by the selectielijstklasse
        ResultaatFactory(zaak=zaak, resultaattype__archiefactietermijn=None)
        calculator = BrondatumCalculator(zaak, datetime.now())
        self.assertIsNone(calculator.calculate())
