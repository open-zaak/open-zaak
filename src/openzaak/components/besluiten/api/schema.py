# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from notifications_api_common.utils import notification_documentation

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

custom_settings = {
    "TITLE": "Besluiten API",
    "VERSION": settings.BESLUITEN_API_VERSION,
    "DESCRIPTION": description,
    "SERVERS": [{"url": "/besluiten/api/v1"}],
    "TAGS": [{"name": "besluiten"}, {"name": "besluitinformatieobjecten"}],
}
