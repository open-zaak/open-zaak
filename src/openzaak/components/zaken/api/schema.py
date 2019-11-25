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

* [Documentatie](https://zaakgerichtwerken.vng.cloud/standaard)
* [Zaakgericht werken](https://zaakgerichtwerken.vng.cloud)
"""

info = openapi.Info(
    title=f"Zaken API",
    default_version=settings.API_VERSION,
    description=description,
    contact=openapi.Contact(
        email="support@maykinmedia.nl", url="https://www.maykinmedia.nl"
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)
