# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Defines the scopes used in the ZRC component.

The Exxellence authorisation model is taken into consideration as well, see
https://wiki.exxellence.nl/display/KPORT/2.+Zaaktype+autorisaties
"""

from vng_api_common.scopes import Scope

SCOPE_ZAKEN_CREATE = Scope(
    "zaken.aanmaken",
    description="""
**Laat toe om**:

* een zaak aan te maken
* de eerste status bij een zaak te zetten
* zaakobjecten aan te maken
* rollen aan te maken
""",
)

SCOPE_ZAKEN_BIJWERKEN = Scope(
    "zaken.bijwerken",
    description="""
**Laat toe om**:

* attributen van een zaak te wijzingen
""",
)

SCOPE_STATUSSEN_TOEVOEGEN = Scope(
    "zaken.statussen.toevoegen",
    description="""
**Laat toe om**:

* Statussen toe te voegen voor een zaak
""",
)

SCOPE_ZAKEN_ALLES_LEZEN = Scope(
    "zaken.lezen",
    description="""
**Laat toe om**:

* zaken op te lijsten
* zaken te doorzoeken
* zaakdetails op te vragen
* statussen te lezen
* statusdetails op te vragen
* zaakobjecten te lezen
* zaakobjectdetails op te vragen
""",
)


SCOPE_ZAKEN_ALLES_VERWIJDEREN = Scope(
    "zaken.verwijderen",
    description="""
**Laat toe om**:

* zaken te verwijderen
""",
)


SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN = Scope(
    "zaken.geforceerd-bijwerken",
    description="""
**Allows**:

* change attributes of all cases including closed ones
""",
)

SCOPEN_ZAKEN_HEROPENEN = Scope(
    "zaken.heropenen",
    description="""
**Allows**:

* reopen cases via creating new statuses after the final one
""",
)
