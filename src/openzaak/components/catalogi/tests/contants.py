# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)

BrondatumArchiefprocedureExampleMapping = {
    Afleidingswijze.afgehandeld: {
        "afleidingswijze": Afleidingswijze.afgehandeld,
        "procestermijn": None,
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.ander_datumkenmerk: {
        "afleidingswijze": Afleidingswijze.ander_datumkenmerk,
        "procestermijn": None,
        "datumkenmerk": "identificatie",
        "einddatum_bekend": False,
        "objecttype": "pand",
        "registratie": "test",
    },
    Afleidingswijze.eigenschap: {
        "afleidingswijze": Afleidingswijze.eigenschap,
        "procestermijn": None,
        "datumkenmerk": "identificatie",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.gerelateerde_zaak: {
        "afleidingswijze": Afleidingswijze.gerelateerde_zaak,
        "procestermijn": None,
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.hoofdzaak: {
        "afleidingswijze": Afleidingswijze.hoofdzaak,
        "procestermijn": None,
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.ingangsdatum_besluit: {
        "afleidingswijze": Afleidingswijze.ingangsdatum_besluit,
        "procestermijn": None,
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.termijn: {
        "afleidingswijze": Afleidingswijze.termijn,
        "procestermijn": "P5M",
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.vervaldatum_besluit: {
        "afleidingswijze": Afleidingswijze.vervaldatum_besluit,
        "procestermijn": None,
        "datumkenmerk": "",
        "einddatum_bekend": False,
        "objecttype": "",
        "registratie": "",
    },
    Afleidingswijze.zaakobject: {
        "afleidingswijze": Afleidingswijze.zaakobject,
        "procestermijn": None,
        "datumkenmerk": "identificatie",
        "einddatum_bekend": False,
        "objecttype": "pand",
        "registratie": "",
    },
}
