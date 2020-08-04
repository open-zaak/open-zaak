# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from drf_yasg import openapi
from vng_api_common.notifications.utils import notification_documentation

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

info = openapi.Info(
    title="Zaken API",
    default_version=settings.ZAKEN_API_VERSION,
    description=description,
    contact=openapi.Contact(
        email=settings.OPENZAAK_API_CONTACT_EMAIL, url=settings.OPENZAAK_API_CONTACT_URL
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)
