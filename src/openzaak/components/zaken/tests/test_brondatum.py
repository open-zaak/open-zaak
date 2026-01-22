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

from ...archiving import try_calculate_archiving
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
            einddatum=date(2024, 1, 1),
            startdatum_bewaartermijn=None,
            archiefactiedatum=None,
        )

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()

        self.assertEqual(zaak.startdatum_bewaartermijn, date(2024, 1, 1))
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))
        self.assertIsNotNone(zaak.archiefnominatie)

    def test_try_calculate_archiving_respects_existing_data(self):
        manual_date = date(2040, 1, 1)
        manual_start = date(2024, 1, 1)

        zaak = ZaakFactory.create(
            einddatum=date(2024, 1, 1),
            archiefactiedatum=manual_date,
            startdatum_bewaartermijn=manual_start,
        )

        try_calculate_archiving(zaak)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, manual_date)
        self.assertEqual(zaak.startdatum_bewaartermijn, manual_start)

    def test_archiving_is_calculated_after_besluit_with_vervaldatum(self):
        zaak = ZaakFactory.create(
            einddatum=date(2020, 1, 1),
            startdatum_bewaartermijn=None,
            archiefactiedatum=None,
            archiefnominatie="blijvend",
        )

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )

        BesluitFactory.create(
            zaak=zaak,
            datum=date(2020, 1, 1),
            ingangsdatum=date(2020, 1, 1),
            vervaldatum=date(2020, 1, 2),
        )

        try_calculate_archiving(zaak)

        zaak.refresh_from_db()
        self.assertIsNotNone(zaak.startdatum_bewaartermijn)
        self.assertIsNotNone(zaak.archiefactiedatum)

    def test_archiving_is_calculated_after_setting_eigenschap_later(self):
        zaak = ZaakFactory.create(einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            resultaattype__brondatum_archiefprocedure_datumkenmerk="expiryDate",
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()

        self.assertIsNone(zaak.archiefactiedatum)

        ZaakEigenschapFactory.create(
            zaak=zaak,
            _naam="expiryDate",
            waarde="2024-01-01T00:00:00Z",
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()

        self.assertIsNotNone(zaak.archiefactiedatum)

    def test_archiving_is_calculated_when_vervaldatum_is_set_later(self):
        zaak = ZaakFactory.create(einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit,
        )

        besluit = BesluitFactory.create(
            zaak=zaak,
            vervaldatum=None,
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()

        self.assertIsNone(zaak.archiefactiedatum)

        besluit.vervaldatum = date(2024, 1, 1)
        besluit.save()

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()

        self.assertIsNotNone(zaak.archiefactiedatum)

    def test_archiving_postponed_without_besluiten_ingangsdatum(self):
        zaak = ZaakFactory.create(einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_archiving_postponed_without_relevante_zaken(self):
        zaak = ZaakFactory.create(einddatum=date(2024, 1, 1))

        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__archiefactietermijn="P5Y",
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak,
        )

        try_calculate_archiving(zaak)
        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)
