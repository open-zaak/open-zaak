from django.conf import settings

from drf_yasg import openapi
from vng_api_common.notifications.utils import notification_documentation

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

* [Documentatie](https://zaakgerichtwerken.vng.cloud/standaard)
* [Zaakgericht werken](https://zaakgerichtwerken.vng.cloud)
"""

info = openapi.Info(
    title=f"Autorisaties API",
    default_version=settings.API_VERSION,
    description=description,
    contact=openapi.Contact(
        email="support@maykinmedia.nl", url="https://www.maykinmedia.nl"
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)
