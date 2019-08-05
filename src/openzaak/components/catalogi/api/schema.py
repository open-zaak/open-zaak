from django.conf import settings

from drf_yasg import openapi

# from .kanalen import KANAAL_CATALOGI

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

**Autorisatie**

Deze API vereist autorisatie. Je kan de
[token-tool](https://zaken-auth.vng.cloud/) gebruiken om JWT-tokens te
genereren.
"""
# **Notificaties**
#
# Deze API publiceert notificaties op het kanaal `{KANAAL_CATALOGI.label}`.
"""

**Handige links**

* [Documentatie](https://zaakgerichtwerken.vng.cloud/standaard)
* [Zaakgericht werken](https://zaakgerichtwerken.vng.cloud)
"""

info = openapi.Info(
    title=f"{settings.PROJECT_NAME} API",
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
