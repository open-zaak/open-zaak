from datetime import datetime

from django.test import TestCase

from openzaak.components.zaken.brondatum import BrondatumCalculator
from openzaak.components.zaken.tests.factories import ResultaatFactory, ZaakFactory


class BronDatumTests(TestCase):
    def test_calculate_brondatum_without_archiefactietermijn(self):
        zaak = ZaakFactory()
        resultaat = ResultaatFactory(zaak=zaak)
        # when archiefactietermijn is not set it is set by the selectielijstklasse
        resultaat.resultaattype.archiefactietermijn = None
        calculator = BrondatumCalculator(zaak, datetime.now())
        self.assertIsNone(calculator.calculate())
