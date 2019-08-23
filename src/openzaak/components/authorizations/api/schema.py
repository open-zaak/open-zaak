from django.conf import settings

from drf_yasg import openapi

description = f"""Een API om een autorisatiecomponent te benaderen.

De `AUTORISATIE` is het kernobject in deze API. Autorisaties worden toegekend
aan applicaties. Een applicatie is een representatie van een (web) app die
communiceert met de API van (andere) componenten, zoals het ZRC, DRC, ZTC en
BRC.

Deze API laat toe om autorisaties van een (taak)applicatie te beheren en uit
te lezen.

**Autorisatie**

Deze API vereist autorisatie. Je kan de
[token-tool](https://ref.tst.vng.cloud/tokens/) gebruiken om JWT-tokens te
genereren.

**Notificaties**

Deze component publiceert notificaties op het kanaal `TODO`.

**Handige links**

* [Aan de slag](https://ref.tst.vng.cloud/ontwikkelaars/)
* ["Papieren" standaard](https://ref.tst.vng.cloud/standaard/)
"""

info = openapi.Info(
    title="Autorisatiecomponent (AC) API",
    default_version=settings.API_VERSION,
    description=description,
    contact=openapi.Contact(
        email="support@maykinmedia.nl",
        url="https://github.com/VNG-Realisatie/gemma-zaken",
    ),
    license=openapi.License(
        name="EUPL 1.2", url="https://opensource.org/licenses/EUPL-1.2"
    ),
)
