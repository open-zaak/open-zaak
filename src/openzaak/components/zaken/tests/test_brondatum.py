# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from datetime import date, datetime
from unittest.mock import patch

from django.test import TestCase

from rest_framework.test import APITestCase
from vng_api_common.constants import BrondatumArchiefprocedureAfleidingswijze

from openzaak.components.zaken.brondatum import BrondatumCalculator
from openzaak.components.zaken.tests.factories import (
    ResultaatFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
)

from ...besluiten.tests.factories import BesluitFactory


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


class ZaakArchivingCalculationTests(APITestCase):
    def test_try_calculate_archiving_fills_empty_fields(self):
        zaak = ZaakFactory.create(
            closed=True,
            einddatum=date(2024, 1, 1),
            startdatum_bewaartermijn=None,
            archiefactiedatum=None,
        )

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )

        zaak.refresh_from_db()

        self.assertEqual(zaak.startdatum_bewaartermijn, date(2024, 1, 1))
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_archiving_is_calculated_after_besluit_with_vervaldatum(self):
        zaak = ZaakFactory.create(
            closed=True,
            einddatum=date(2020, 1, 1),
            startdatum_bewaartermijn=None,
            archiefactiedatum=None,
            archiefnominatie="blijvend",
        )

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__archiefnominatie="blijvend_bewaren",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit,
        )

        BesluitFactory.create(
            zaak=zaak,
            datum=date(2020, 1, 1),
            ingangsdatum=date(2020, 1, 1),
            vervaldatum=date(2020, 1, 2),
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.startdatum_bewaartermijn, date(2020, 1, 2))
        self.assertEqual(zaak.archiefactiedatum, date(2025, 1, 2))
        self.assertEqual(zaak.archiefnominatie, "blijvend_bewaren")

    def test_archiving_is_calculated_after_setting_eigenschap_later(self):
        zaak = ZaakFactory.create(closed=True, einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__archiefnominatie="blijvend_bewaren",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            resultaattype__brondatum_archiefprocedure_datumkenmerk="expiryDate",
        )

        zaak.refresh_from_db()

        self.assertIsNone(zaak.archiefactiedatum)

        ZaakEigenschapFactory.create(
            zaak=zaak,
            _naam="expiryDate",
            waarde="2024-01-01T00:00:00Z",
        )

        zaak.refresh_from_db()

        self.assertEqual(zaak.startdatum_bewaartermijn, date(2024, 1, 1))
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))
        self.assertEqual(zaak.archiefnominatie, "blijvend_bewaren")

    def test_archiving_postponed_without_besluiten_ingangsdatum(self):
        zaak = ZaakFactory.create(closed=True, einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_archiving_postponed_without_relevante_zaken(self):
        zaak = ZaakFactory.create(closed=True, einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak,
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)
