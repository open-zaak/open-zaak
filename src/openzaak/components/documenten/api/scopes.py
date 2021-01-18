# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Defines the scopes used in the DRC component.
"""

from vng_api_common.scopes import Scope

SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN = Scope(
    "documenten.verwijderen",
    description="""
**Laat toe om**:

* documenten te verwijderen
""",
)

SCOPE_DOCUMENTEN_ALLES_LEZEN = Scope(
    "documenten.lezen",
    description="""
**Laat toe om**:

* documenten te lezen
* documentdetails op te vragen
""",
)

SCOPE_DOCUMENTEN_BIJWERKEN = Scope(
    "documenten.bijwerken",
    description="""
**Laat toe om**:

* attributen van een document te wijzingen
""",
)

SCOPE_DOCUMENTEN_AANMAKEN = Scope(
    "documenten.aanmaken",
    description="""
**Laat toe om**:

* documenten aan te maken
""",
)

SCOPE_DOCUMENTEN_LOCK = Scope(
    "documenten.lock",
    description="""
**Allows**:

* to lock documents
* to unlock documents
""",
)

SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK = Scope(
    "documenten.geforceerd-unlock",
    description="""
**Allows**:

* to unlock documents without lock key
""",
)
