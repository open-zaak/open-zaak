# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime, time

from openzaak.utils.exceptions import DetermineProcessEndDateException


def try_calculate_archiving(zaak):
    if not zaak.einddatum:
        return
    if not hasattr(zaak, "resultaat"):
        return
    if zaak.startdatum_bewaartermijn and zaak.archiefactiedatum:
        return

    from openzaak.components.zaken.brondatum import BrondatumCalculator

    datum_status_gezet = datetime.combine(
        zaak.einddatum,
        time.min,
    )

    brondatum_calculator = BrondatumCalculator(
        zaak,
        datum_status_gezet=datum_status_gezet,
    )
    try:
        archiefactiedatum = brondatum_calculator.calculate()
    except DetermineProcessEndDateException:
        return

    if archiefactiedatum is None:
        return

    zaak.archiefactiedatum = archiefactiedatum
    zaak.startdatum_bewaartermijn = brondatum_calculator.brondatum
    zaak.archiefnominatie = brondatum_calculator.get_archiefnominatie()

    zaak.save(
        update_fields=[
            "startdatum_bewaartermijn",
            "archiefactiedatum",
            "archiefnominatie",
        ]
    )
