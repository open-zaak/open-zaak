# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.core.management.base import BaseCommand

from openzaak.components.zaken.api.validators import match_eigenschap_specificatie
from openzaak.components.zaken.models import ZaakEigenschap


class Command(BaseCommand):
    help = (
        "Validate zaak-eigenschap.waarde against the related "
        "eigenschap.specificatie and display not compliant zaak-eigenschappen"
    )

    def handle(self, **options):
        # check only resources with local eigenschap
        zaakeigenschappen = (
            ZaakEigenschap.objects.select_related(
                "zaak", "_eigenschap", "_eigenschap__specificatie_van_eigenschap"
            )
            .filter(
                _eigenschap__isnull=False,
                _eigenschap__specificatie_van_eigenschap__isnull=False,
            )
            .order_by("zaak", "_naam")
        )

        if not zaakeigenschappen.exists():
            self.stdout.write("There are no zaak-eigenschappen to check")
            return

        self.stdout.write(
            f"Starting validation of {zaakeigenschappen.count()} zaak-eigenschappen"
        )
        total_invalid = 0
        for zaakeigenschap in zaakeigenschappen:
            specificatie = zaakeigenschap._eigenschap.specificatie_van_eigenschap
            valid = match_eigenschap_specificatie(
                specificatie,
                zaakeigenschap.waarde,
            )
            if not valid:
                self.stdout.write(
                    f"Zaak {zaakeigenschap.zaak.uuid} has Eigenschap {zaakeigenschap.uuid} "
                    f"with waarde='{zaakeigenschap.waarde}' that does not match specificatie {specificatie}"
                )
                total_invalid += 1

        if total_invalid:
            self.stdout.write(
                self.style.WARNING(
                    f"There are {total_invalid} zaak-eigenschappen with invalid values"
                )
            )

        else:
            self.stdout.write(
                self.style.SUCCESS("All zaak-eigenschappen have valid values")
            )
