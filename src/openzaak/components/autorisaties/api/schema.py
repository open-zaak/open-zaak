# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from notifications_api_common.utils import notification_documentation

from openzaak.utils.apidoc import DOC_AUTH_JWT

from .kanalen import KANAAL_AUTORISATIES

description = f"""Een API om een autorisatiecomponent (AC) te benaderen.

De `AUTORISATIE` is het kernobject in deze API. Autorisaties worden toegekend
aan applicaties. Een applicatie is een representatie van een (web) app die
communiceert met de API van (andere) componenten, zoals het ZRC, DRC, ZTC en
BRC.

Deze API laat toe om autorisaties van een (taak)applicatie te beheren en uit
te lezen.

**Afhankelijkheden**

Deze API is afhankelijk van:

* Notificaties API

{DOC_AUTH_JWT}

### Notificaties

{notification_documentation(KANAAL_AUTORISATIES)}

**Handige links**

* [API-documentatie]({settings.DOCUMENTATION_URL})
* [Open Zaak documentatie]({settings.OPENZAAK_DOCS_URL})
* [Zaakgericht werken]({settings.ZGW_URL})
* [Open Zaak GitHub]({settings.OPENZAAK_GITHUB_URL})
"""


custom_settings = {
    "TITLE": "Autorisaties API",
    "VERSION": settings.AUTORISATIES_API_VERSION,
    "DESCRIPTION": description,
    "SERVERS": [{"url": "/autorisaties/api/v1"}],
    "TAGS": [{"name": "applicaties"}],
}
