# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, datetime, time

from openzaak.components.zaken.models import Zaak
from openzaak.utils.exceptions import DetermineProcessEndDateException


def calculate_archiving_data(
    zaak: Zaak,
    datum_status_gezet: datetime | None = None,
    *,
    force: bool = False,
) -> dict[str, str | date | None]:
    if not zaak.einddatum or not hasattr(zaak, "resultaat"):
        return {}

    from openzaak.components.zaken.brondatum import BrondatumCalculator

    if datum_status_gezet is None:
        datum_status_gezet = datetime.combine(zaak.einddatum, time.min)

    calculator = BrondatumCalculator(
        zaak,
        datum_status_gezet=datum_status_gezet,
        force=force,
    )

    try:
        archiefactiedatum = calculator.calculate()
    except (DetermineProcessEndDateException, ValueError):
        return {}

    if archiefactiedatum is None:
        return {}

    return {
        "archiefactiedatum": archiefactiedatum,
        "startdatum_bewaartermijn": calculator.brondatum,
        "archiefnominatie": calculator.get_archiefnominatie(),
    }


def try_calculate_archiving(zaak, *, force=False):
    data = calculate_archiving_data(zaak, force=force)
    if not data:
        return

    for field, value in data.items():
        setattr(zaak, field, value)

    zaak.save(update_fields=list(data.keys()))
