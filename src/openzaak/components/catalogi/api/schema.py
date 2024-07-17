# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from notifications_api_common.utils import notification_documentation

from openzaak.utils.apidoc import DOC_AUTH_JWT

from .kanalen import KANAAL_BESLUITTYPEN, KANAAL_INFORMATIEOBJECTTYPEN, KANAAL_ZAAKTYPEN

description = f"""Een API om een zaaktypecatalogus (ZTC) te benaderen.

De zaaktypecatalogus helpt gemeenten om het proces vanuit de 'vraag van een
klant' (productaanvraag, melding, aangifte, informatieverzoek e.d.) tot en met
het leveren van een passend antwoord daarop in te richten, inclusief de
bijbehorende informatievoorziening.

Een CATALOGUS bestaat uit ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn en
wordt typisch gebruikt om een ZAAK (in de Zaken API), INFORMATIEOBJECT (in de
Documenten API) en BESLUIT (in de Besluiten API) te voorzien van type,
standaardwaarden en processtructuur.

**Afhankelijkheden**

Deze API is afhankelijk van:

* Gemeentelijke Selectielijst API
* Autorisaties API *(optioneel)*

{DOC_AUTH_JWT}

### Notificaties

{notification_documentation(KANAAL_ZAAKTYPEN)}

{notification_documentation(KANAAL_BESLUITTYPEN)}

{notification_documentation(KANAAL_INFORMATIEOBJECTTYPEN)}

**Handige links**

* [API-documentatie]({settings.DOCUMENTATION_URL})
* [Open Zaak documentatie]({settings.OPENZAAK_DOCS_URL})
* [Zaakgericht werken]({settings.ZGW_URL})
* [Open Zaak GitHub]({settings.OPENZAAK_GITHUB_URL})
"""

custom_settings = {
    "TITLE": "Catalogi API",
    "VERSION": settings.CATALOGI_API_VERSION,
    "DESCRIPTION": description,
    "SERVERS": [{"url": "/catalogi/api/v1"}],
    "TAGS": [
        {"name": "besluittypen"},
        {"name": "catalogussen"},
        {"name": "eigenschappen"},
        {"name": "informatieobjecttypen"},
        {"name": "resultaattypen"},
        {"name": "roltypen"},
        {"name": "statustypen"},
        {"name": "zaakobjecttypen"},
        {"name": "zaaktype-informatieobjecttypen"},
        {"name": "zaaktypen"},
    ],
}
