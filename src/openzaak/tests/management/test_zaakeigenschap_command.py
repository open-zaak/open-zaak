# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from openzaak.components.catalogi.constants import FormaatChoices
from openzaak.components.catalogi.tests.factories import EigenschapFactory
from openzaak.components.zaken.tests.factories import ZaakEigenschapFactory


class ZaakEigenschapCommandTests(TestCase):
    """
    test 'check_zaak_eigenschappen' command
    """

    def test_valid(self):
        stdout, stderr = StringIO(), StringIO()

        eigenschap = EigenschapFactory.create(
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__lengte="10",
        )
        ZaakEigenschapFactory.create(
            eigenschap=eigenschap,
            waarde="some text",
            zaak__zaaktype=eigenschap.zaaktype,
        )

        call_command(
            "check_zaak_eigenschappen", stdout=stdout, stderr=stderr, no_color=True
        )

        command_output = stdout.getvalue().splitlines()
        expected_output = [
            "Starting validation of 1 zaak-eigenschappen",
            "All zaak-eigenschappen have valid values",
        ]
        self.assertEqual(command_output, expected_output)

    def test_invalid(self):
        stdout, stderr = StringIO(), StringIO()

        eigenschap = EigenschapFactory.create(
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__lengte="4",
        )
        ZaakEigenschapFactory.create(
            eigenschap=eigenschap, waarde="test", zaak__zaaktype=eigenschap.zaaktype
        )
        ze_invalid = ZaakEigenschapFactory.create(
            eigenschap=eigenschap,
            waarde="some text",
            zaak__zaaktype=eigenschap.zaaktype,
        )

        call_command(
            "check_zaak_eigenschappen", stdout=stdout, stderr=stderr, no_color=True
        )

        command_output = stdout.getvalue().splitlines()
        expected_output = [
            "Starting validation of 2 zaak-eigenschappen",
            (
                f"Zaak {ze_invalid.zaak.uuid} has Eigenschap {ze_invalid.uuid} "
                f"with waarde='{ze_invalid.waarde}' that does not match specificatie "
                f"{eigenschap.specificatie_van_eigenschap}"
            ),
            "There are 1 zaak-eigenschappen with invalid values",
        ]
        self.assertEqual(command_output, expected_output)

    def test_no_data(self):
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "check_zaak_eigenschappen", stdout=stdout, stderr=stderr, no_color=True
        )

        command_output = stdout.getvalue().splitlines()
        expected_output = ["There are no zaak-eigenschappen to check"]
        self.assertEqual(command_output, expected_output)
