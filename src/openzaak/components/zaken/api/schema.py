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

### Expand: afwijking van de standaard

De Zaken API 1.6.0-standaard staat het uitbreiden van gerelateerde resources met
`expand` tot een willekeurige diepte toe. Open Zaak wijkt hiervan af: alleen de
expliciet ondersteunde expand-paden zijn beschikbaar, met maximaal drie niveaus
van nesting. Niet ieder pad tot en met drie niveaus wordt ondersteund. Raadpleeg
de toegestane waarden van `expand` bij de betreffende operatie.

Bijvoorbeeld: `hoofdzaak.status.statustype` omvat drie niveaus. Gebruik bij het
opvragen van zaken
`expand=hoofdzaak,hoofdzaak.status,hoofdzaak.status.statustype` om ook de
bovenliggende resources mee te nemen. Diepere of niet-vermelde expand-paden
worden niet ondersteund.

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
        {"name": "zaaknotities"},
        {"name": "klantcontacten"},
    ],
}
