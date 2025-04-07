# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from vng_api_common.constants import RolOmschrijving

from openzaak.components.catalogi.models import RolType
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory


class RolTypeModelTests(TestCase):
    def setUp(self):
        self.zaaktype = ZaakTypeFactory()

    @patch("openzaak.components.catalogi.models.roltype.validate_zaaktype_concept")
    def test_clean_valid_case_calls_validator(self, mock_validator):
        roltype = RolType(
            omschrijving="Behandelaar",
            omschrijving_generiek=RolOmschrijving.behandelaar,
            zaaktype=self.zaaktype,
        )

        roltype.clean()

        mock_validator.assert_called_once_with(self.zaaktype)

    def test_clean_without_zaaktype_raises_error(self):
        roltype = RolType(
            omschrijving="Behandelaar",
            omschrijving_generiek=RolOmschrijving.behandelaar,
            zaaktype=None,
        )

        with self.assertRaises(ValidationError) as ctx:
            roltype.clean()

        self.assertIn("zaaktype", ctx.exception.message_dict)
        self.assertEqual(
            ctx.exception.message_dict["zaaktype"][0], "Zaaktype mag niet leeg zijn."
        )

    def test_clean_with_zaaktype_does_not_raise(self):
        roltype = RolType(
            omschrijving="Initiator",
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype=self.zaaktype,
        )

        roltype.clean()
