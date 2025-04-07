from django.test import TestCase
from django.core.exceptions import ValidationError
from vng_api_common.constants import RolOmschrijving

from openzaak.components.catalogi.models import RolType
from unittest.mock import patch

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory


class RolTypeModelTests(TestCase):
    def setUp(self):
        self.zaaktype = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            identificatie=1,
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
        )

    def test_clean_raises_validation_error_if_zaaktype_is_none(self):
        roltype = RolType(
            omschrijving="Testrol zonder zaaktype",
            omschrijving_generiek=RolOmschrijving.initiator,
        )

        with self.assertRaises(ValidationError) as context:
            roltype.clean()

        self.assertIn("zaaktype", context.exception.message_dict)
        self.assertEqual(
            context.exception.message_dict["zaaktype"][0],
            "Zaaktype mag niet leeg zijn."
        )

    def test_clean_passes_with_valid_zaaktype(self):
        roltype = RolType(
            omschrijving="Testrol met zaaktype",
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype=self.zaaktype,
        )

        try:
            roltype.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    @patch("openzaak.components.catalogi.models.validate_zaaktype_concept")
    def test_clean_calls_validate_zaaktype_concept(self, mock_validate):
        roltype = RolType(
            omschrijving="Testrol",
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype=self.zaaktype,
        )

        roltype.clean()
        mock_validate.assert_called_once_with(self.zaaktype)

    @patch("openzaak.components.catalogi.models.validate_zaaktype_concept")
    def test_clean_raises_if_validate_zaaktype_concept_fails(self, mock_validate):
        mock_validate.side_effect = ValidationError({"zaaktype": "Concept niet toegestaan."})

        roltype = RolType(
            omschrijving="Testrol fout",
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype=self.zaaktype,
        )

        with self.assertRaises(ValidationError) as context:
            roltype.clean()

        self.assertIn("zaaktype", context.exception.message_dict)
        self.assertEqual(context.exception.message_dict["zaaktype"][0], "Concept niet toegestaan.")
