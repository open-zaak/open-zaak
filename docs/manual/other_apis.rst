.. _manual_other_apis:

=========================
Gebruik van externe API's
=========================

Open Zaak past de Common Ground gedachte toe van data-bij-de-bron ophalen. Er bestaan
al een aantal RESTful API's die gebruikt kunnen worden met Open Zaak, zoals de `BAG`_ en
`BRT`_. Een praktisch voorbeeld hiervan is het relateren van een **Pand** of **Wegdeel**
aan een zaak.

Deze API's hebben echter vaak hun eigen authenticatie-mechanisme, zelfs als het Open
Data betreft - vaak ter voorkoming van misbruik. Er zijn twee mogelijke pistes om deze
APIs te kunnen gebruiken met Open Zaak:

* Instellen van :ref:`manual_other_apis_auth` voor deze API's
* API's consumeren via :ref:`manual_other_apis_nlx`

Deze kunnen ook gecombineerd worden - consumeren via NLX én gebruik van een API key.

.. _BAG: https://www.pdok.nl/restful-api/-/article/basisregistratie-adressen-en-gebouwen-ba-1
.. _BRT: https://www.pdok.nl/restful-api/-/article/basisregistratie-topografie-brt-topnl

.. _manual_other_apis_auth:

Authenticatie
=============

De Kadaster en HaalCentraal API's vereisen typisch authenticatie met een *API key*.
Consulteer de documentatie van de betreffende API om een API key te verkrijgen.

Navigeer daarna in de **admin interface** naar **API Autorisaties** en klik op
**Other external API credentials**.

Klik rechtsboven op **Other external API credential toevoegen** en vul de velden in:

API-root
    de basis-URL waar de API beschikbaar is, bijvoorbeeld
    ``http://bag.basisregistraties.overheid.nl/api/v1``

Label
    Een omschrijving zodat je herkent om welke API het gaat, bijvoorbeeld "BAG".

Header key
    De naam van de HTTP header waar de API key in gaat, bijvoorbeeld ``X-Api-Key`` of
    ``Authorization``.

Header value
    De waarde van de API key die je eerder verkreeg.

Klik tot slot op **Opslaan**.

.. note:: Bij het aanmaken van bijvoorbeeld ZaakObjecten wordt er gevalideerd dat de URL
   van het object geldig is. Om dit te kunnen doen, moet Open Zaak weten hoe zich te
   autoriseren voor deze URL. De bovenstaande procedure maakt dit mogelijk.

.. _manual_other_apis_nlx:

NLX
====

`NLX`_ faciliteert data-uitwisseling voor overheden en organisaties. Open Zaak
heeft functionaliteiten die het gebruik van NLX aanmoedigen.

Organisaties kunnen ervoor kiezen om de gegevens via NLX te ontsluiten in een opzet
waarbij geen API key nodig is voor de consumer, zolang deze maar via het NLX netwerk
de gegevens opvraagt.

Open Zaak kan deze "publieke" URLs vertalen naar NLX-specifieke URLs zodat de gegevens
via het NLX netwerk opgevraagd worden. Hiervoor moet je een *NLX outway* beschikbaar
hebben.

Navigeer in de **admin interface** naar **Configuratie** > **URL rewrites**. Klik op
**URL Rewrite toevoegen** en vul het formulier in:

From value:
    Het beginstuk van de URL die je wenst om te zetten. Bijvoorbeeld
    ``http://bag.basisregistraties.overheid.nl/api/v1``

To value:
    De equivalente URL in je outway, bijvoorbeeld
    ``http://my-outway:8443/kadaster/bag``.

.. note:: Consulteer de NLX directory om te zien welke services beschikbaar zijn.

.. _NLX: https://nlx.io
