from django.conf import settings

from drf_yasg import openapi

from .kanalen import KANAAL_DOCUMENTEN

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

**Afhankelijkheden**

Deze API is afhankelijk van:

* Catalogi API
* Notificaties API
* Autorisaties API *(optioneel)*
* Zaken API *(optioneel)*

**Autorisatie**

Deze API vereist autorisatie. Je kan de
[token-tool](https://zaken-auth.vng.cloud/) gebruiken om JWT-tokens te
genereren.

**Notificaties**

Deze API publiceert notificaties op het kanaal `{KANAAL_DOCUMENTEN.label}`.

**Handige links**

* [Documentatie](https://zaakgerichtwerken.vng.cloud/standaard)
* [Zaakgericht werken](https://zaakgerichtwerken.vng.cloud)
"""

info = openapi.Info(
    title="DOCUMENTEN API",
    default_version=settings.API_VERSION,
    description=description,
    contact=openapi.Contact(
        email="standaarden.ondersteuning@vng.nl",
        url="https://zaakgerichtwerken.vng.cloud"
    ),
    license=openapi.License(
        name="EUPL 1.2",
        url='https://opensource.org/licenses/EUPL-1.2'
    ),
)
