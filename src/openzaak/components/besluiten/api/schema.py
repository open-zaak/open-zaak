# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from drf_yasg import openapi
from vng_api_common.notifications.utils import notification_documentation

from openzaak.utils.apidoc import DOC_AUTH_JWT

from .kanalen import KANAAL_BESLUITEN

description = f"""Een API om een besluitregistratiecomponent (BRC) te benaderen.

Een BESLUIT wordt veelal schriftelijk vastgelegd maar dit is niet
noodzakelijk. Omgekeerd kan het voorkomen dat in een INFORMATIEOBJECT meerdere
besluiten vastgelegd zijn. Vandaar de N:M-relatie naar INFORMATIEOBJECT. Een
besluit komt voort uit een zaak van de zaakbehandelende organisatie dan wel is
een besluit van een andere organisatie dat het onderwerp (object) is van een
zaak van de zaakbehandelende organisatie. BESLUIT heeft dan ook een optionele
relatie met de ZAAK waarvan het een uitkomst is.

De typering van BESLUITen is in de Catalogi API (ZTC) ondergebracht in de vorm
van BESLUITTYPEn.

**Afhankelijkheden**

Deze API is afhankelijk van:

* Catalogi API
* Notificaties API
* Documenten API *(optioneel)*
* Zaken API *(optioneel)*
* Autorisaties API *(optioneel)*

{DOC_AUTH_JWT}

### Notificaties

{notification_documentation(KANAAL_BESLUITEN)}

**Handige links**

* [API-documentatie]({settings.DOCUMENTATION_URL})
* [Open Zaak documentatie]({settings.OPENZAAK_DOCS_URL})
* [Zaakgericht werken]({settings.ZGW_URL})
* [Open Zaak GitHub]({settings.OPENZAAK_GITHUB_URL})
"""

info = openapi.Info(
    title="Besluiten API",
    default_version=settings.BESLUITEN_API_VERSION,
    description=description,
    contact=openapi.Contact(
        email=settings.OPENZAAK_API_CONTACT_EMAIL, url=settings.OPENZAAK_API_CONTACT_URL
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)
