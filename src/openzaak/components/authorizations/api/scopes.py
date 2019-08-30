"""
Defines the scopes used in the ZRC component.

The Exxellence authorisation model is taken into consideration as well, see
https://wiki.exxellence.nl/display/KPORT/2.+Zaaktype+autorisaties
"""

from vng_api_common.scopes import Scope

SCOPE_AUTORISATIES_LEZEN = Scope(
    "autorisaties.lezen",
    description="""
**Laat toe om**:

* autorisaties te lezen
""",
)

SCOPE_AUTORISATIES_BIJWERKEN = Scope(
    "autorisaties.bijwerken",
    description="""
**Laat toe om**:

* autorisaties te maken
* autorisaties te wijzigen
* autorisaties te verwijderen
""",
)
