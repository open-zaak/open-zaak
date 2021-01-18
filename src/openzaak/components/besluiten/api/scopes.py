# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Defines the scopes used in the BRC component.
"""

from vng_api_common.scopes import Scope

SCOPE_BESLUITEN_ALLES_VERWIJDEREN = Scope(
    "besluiten.verwijderen",
    description="""
**Laat toe om**:

* besluiten te verwijderen
""",
)

SCOPE_BESLUITEN_ALLES_LEZEN = Scope(
    "besluiten.lezen",
    description="""
**Laat toe om**:

* besluiten te lezen
* besluitdetails op te vragen
""",
)

SCOPE_BESLUITEN_BIJWERKEN = Scope(
    "besluiten.bijwerken",
    description="""
**Laat toe om**:

* attributen van een besluit te wijzingen
""",
)

SCOPE_BESLUITEN_AANMAKEN = Scope(
    "besluiten.aanmaken",
    description="""
**Laat toe om**:

* besluiten aan te maken
""",
)
