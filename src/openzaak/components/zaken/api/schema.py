# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from notifications_api_common.utils import notification_documentation

from openzaak.utils.apidoc import DOC_AUTH_JWT

from .kanalen import KANAAL_ZAKEN

description = f"""Een API om een zaakregistratiecomponent (ZRC) te benaderen.

De ZAAK is het kernobject in deze API, waaraan verschillende andere
resources gerelateerd zijn. De Zaken API werkt samen met andere API's voor
Zaakgericht werken om tot volledige functionaliteit te komen.

**Afhankelijkheden**

Deze API is afhankelijk van:

* Catalogi API
* Notificaties API
* Documenten API *(optioneel)*
* Besluiten API *(optioneel)*
* Autorisaties API *(optioneel)*

{DOC_AUTH_JWT}

### Notificaties

{notification_documentation(KANAAL_ZAKEN)}

**Handige links**

* [API-documentatie]({settings.DOCUMENTATION_URL})
* [Open Zaak documentatie]({settings.OPENZAAK_DOCS_URL})
* [Zaakgericht werken]({settings.ZGW_URL})
* [Open Zaak GitHub]({settings.OPENZAAK_GITHUB_URL})
"""


custom_settings = {
    "TITLE": "Zaken API",
    "VERSION": settings.ZAKEN_API_VERSION,
    "DESCRIPTION": description,
    "SERVERS": [{"url": "/zaken/api/v1"}],
    "TAGS": [
        {"name": "zaken"},
        {"name": "resultaten"},
        {"name": "rollen"},
        {"name": "statussen"},
        {"name": "zaakcontactmomenten"},
        {"name": "zaakinformatieobjecten"},
        {"name": "zaakobjecten"},
        {"name": "zaakverzoeken"},
        {"name": "klantcontacten"},
    ],
}
