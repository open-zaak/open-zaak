# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from humanize import naturalsize
from notifications_api_common.utils import notification_documentation

from openzaak.utils.apidoc import DOC_AUTH_JWT

from .kanalen import KANAAL_DOCUMENTEN

min_upload_size = naturalsize(settings.MIN_UPLOAD_SIZE, binary=True)

description = f"""Een API om een documentregistratiecomponent (DRC) te benaderen.

In een documentregistratiecomponent worden INFORMATIEOBJECTen opgeslagen. Een
INFORMATIEOBJECT is een digitaal document voorzien van meta-gegevens.
INFORMATIEOBJECTen kunnen aan andere objecten zoals zaken en besluiten worden
gerelateerd (maar dat hoeft niet) en kunnen gebruiksrechten hebben.

GEBRUIKSRECHTEN leggen voorwaarden op aan het gebruik van het INFORMATIEOBJECT
(buiten raadpleging). Deze GEBRUIKSRECHTEN worden niet door de API gevalideerd
of gehandhaafd.

De typering van INFORMATIEOBJECTen is in de Catalogi API (ZTC) ondergebracht in
de vorm van INFORMATIEOBJECTTYPEn.

**Uploaden van bestanden**

Binnen deze API bestaan een aantal endpoints die binaire data ontvangen, al
dan niet base64-encoded. Webservers moeten op deze endpoints een minimale
request body size van {min_upload_size} ondersteunen. Dit omvat de JSON van de
metadata EN de base64-encoded bestandsdata. Hou hierbij rekening met de
overhead van base64, die ongeveer 33% bedraagt in worst-case scenario's. Dit
betekent dat bij een limiet van 4GB het bestand maximaal ongeveer 3GB groot
mag zijn.

**Afhankelijkheden**

Deze API is afhankelijk van:

* Catalogi API
* Notificaties API
* Autorisaties API *(optioneel)*
* Zaken API *(optioneel)*

{DOC_AUTH_JWT}

### Notificaties

{notification_documentation(KANAAL_DOCUMENTEN)}

**Handige links**

* [API-documentatie]({settings.DOCUMENTATION_URL})
* [Open Zaak documentatie]({settings.OPENZAAK_DOCS_URL})
* [Zaakgericht werken]({settings.ZGW_URL})
* [Open Zaak GitHub]({settings.OPENZAAK_GITHUB_URL})
"""


custom_settings = {
    "TITLE": "Documenten API",
    "VERSION": settings.DOCUMENTEN_API_VERSION,
    "DESCRIPTION": description,
    "SERVERS": [{"url": "/documenten/api/v1"}],
    "TAGS": [
        {"name": "enkelvoudiginformatieobjecten"},
        {"name": "bestandsdelen"},
        {"name": "gebruiksrechten"},
        {"name": "objectinformatieobjecten"},
        {"name": "verzendingen"},
        {"name": "import"},
    ],
}
