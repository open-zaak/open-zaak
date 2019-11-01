"""
Defines the scopes used in the ZTC component.

We keep things extremely simple - you can either read or write. Currently
writes are not supported yet in the API.
"""
from vng_api_common.scopes import Scope

SCOPE_ZAAKTYPES_READ = Scope(
    "zaaktypes.lezen",
    description="""
**Laat toe om**:

* leesoperaties uit te voeren in de API. Alle resources zijn beschikbaar.
""",
)

SCOPE_ZAAKTYPES_WRITE = Scope(
    "zaaktypes.schrijven",
    description="""
**Laat toe om**:

* schrijfoperaties uit te voeren in de API. Alle resources zijn beschikbaar.
""",
)

SCOPE_ZAAKTYPES_FORCED_DELETE = Scope(
    "zaaktypes.geforceerd_verwijderen",
    description="""
**Laat toe om**:

* Gepubliceerde types geforceerd te verwijderen. Alle resources zijn beschikbaar.
""",
)
