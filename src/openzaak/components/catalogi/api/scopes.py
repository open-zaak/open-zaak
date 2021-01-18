# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Defines the scopes used in the ZTC component.

We keep things extremely simple - you can either read or write. Currently
writes are not supported yet in the API.
"""
from vng_api_common.scopes import Scope

SCOPE_CATALOGI_READ = Scope(
    "catalogi.lezen",
    description="""
**Laat toe om**:

* leesoperaties uit te voeren in de API. Alle resources zijn beschikbaar.
""",
)

SCOPE_CATALOGI_WRITE = Scope(
    "catalogi.schrijven",
    description="""
**Laat toe om**:

* schrijfoperaties uit te voeren in de API. Alle resources zijn beschikbaar.
""",
)

SCOPE_CATALOGI_FORCED_DELETE = Scope(
    "catalogi.geforceerd-verwijderen",
    description="""
**Laat toe om**:

* Gepubliceerde types geforceerd te verwijderen. Alle resources zijn beschikbaar.
""",
)
