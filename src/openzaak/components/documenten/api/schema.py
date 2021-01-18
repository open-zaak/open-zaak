# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import OrderedDict

from django.conf import settings

from drf_yasg import openapi
from humanize import naturalsize
from rest_framework import status
from vng_api_common.inspectors.view import HTTP_STATUS_CODE_TITLES
from vng_api_common.notifications.utils import notification_documentation
from vng_api_common.serializers import FoutSerializer

from openzaak.utils.apidoc import DOC_AUTH_JWT
from openzaak.utils.schema import AutoSchema

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

info = openapi.Info(
    title="Documenten API",
    default_version=settings.DOCUMENTEN_API_VERSION,
    description=description,
    contact=openapi.Contact(
        email=settings.OPENZAAK_API_CONTACT_EMAIL, url=settings.OPENZAAK_API_CONTACT_URL
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)


class EIOAutoSchema(AutoSchema):
    """
    Add the HTTP 413 error response to the schema.

    This is only relevant for endpoints that support file uploads.
    """

    def _get_error_responses(self) -> OrderedDict:
        responses = super()._get_error_responses()

        if self.method not in ["POST", "PUT", "PATCH"]:
            return responses

        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        fout_schema = self.serializer_to_schema(FoutSerializer())
        responses[status_code] = openapi.Response(
            description=HTTP_STATUS_CODE_TITLES.get(status_code, ""), schema=fout_schema
        )

        return responses
