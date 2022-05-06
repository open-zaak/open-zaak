# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import List, Tuple, TypedDict

from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)


class ArchiefProcedure(TypedDict):
    afleidingswijze: str
    datumkenmerk: str
    einddatum_bekend: bool
    objecttype: str
    registratie: str
    procestermijn: str


AFLEIDINGSWIJZE_VALIDATION_RULES = {
    Afleidingswijze.afgehandeld: {
        "procestermijn": False,
        "datumkenmerk": False,
        "einddatum_bekend": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.ander_datumkenmerk: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": True,
        "registratie": True,
    },
    Afleidingswijze.eigenschap: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.gerelateerde_zaak: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.hoofdzaak: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.ingangsdatum_besluit: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.termijn: {
        "procestermijn": True,
        "datumkenmerk": False,
        "einddatum_bekend": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.vervaldatum_besluit: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.zaakobject: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": True,
        "registratie": False,
    },
}


def validate_brondatumarchiefprocedure(
    data: ArchiefProcedure,
) -> Tuple[bool, List[str], List[str]]:
    mapping = AFLEIDINGSWIJZE_VALIDATION_RULES[data["afleidingswijze"]]
    error = False
    empty = []
    required = []
    for key, value in mapping.items():
        if bool(data[key]) != value:
            error = True
            if value:
                required.append(key)
            else:
                empty.append(key)
    return error, empty, required
