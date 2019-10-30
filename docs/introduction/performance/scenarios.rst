=====================
Measuring performance
=====================

.. todo:: This document is in Dutch and is considered for translation.

Goal
====

Het doel van de performance metingen is om inzicht te verkrijgen in de relaties tussen systeemeisen, aantal gebruikers en reactiesnelheid van de API's. Uit deze relaties kunnen we de minimum systeemeisen opstellen, afhankelijk van het aantal gebruikers, waarop de API's nog acceptabel presteren.

Tevens maakt een gestandardiseerde performance meting inzichtelijk welke effect optimalisaties hebben, zodat er doelgericht en aantoonbaar verbeteringen kunnen worden doorgevoerd.

Technische test scenario's
==========================

De performance van enkele veelgebruike API-verzoeken wordt gemeten om inzicht te verkrijgen in de ruwe performance. Het betreft het opvragen en aanmaken van een (hoofd) object en het opvragen van een lijst van (hoofd) objecten van de Zaken, Catalogi, Besluiten en Documenten API's.

**Zaken API**

1. ZAAKen opvragen (``GET /api/v1/zaken``)
2. ZAAK opvragen (``GET /api/v1/zaken/d4d..2e8``)
3. ZAAK aanmaken (``POST /api/v1/zaken``)

**Catalogi API**

1. ZAAKTYPEn opvragen (``GET /api/v1/zaaktypen``)
2. ZAAKTYPE opvragen (``GET /api/v1/zaaktypen/d4d..2e8``)
3. ZAAKTYPE aanmaken (``POST /api/v1/zaaktypen``)

**Besluiten API**

1. BESLUITen opvragen (``GET /api/v1/besluit``)
2. BESLUIT opvragen (``GET /api/v1/besluit/d4d..2e8``)
3. BESLUIT aanmaken (``POST /api/v1/besluit``)

**Documenten API**

1. ENKELVOUDIGINFORMATIEOBJECTen opvragen (``GET /api/v1/enkelvoudiginformatieobjecten``)
2. ENKELVOUDIGINFORMATIEOBJECT opvragen (``GET /api/v1/enkelvoudiginformatieobjecten/d4d..2e8``)
3. ENKELVOUDIGINFORMATIEOBJECT aanmaken (``POST /api/v1/enkelvoudiginformatieobjecten``)

Test specificatie
-----------------

Gebruik van scenario's
~~~~~~~~~~~~~~~~~~~~~~

Een scenario is in deze test specificatie gelijk aan een API-verzoek. Elke API-resource wordt achter elkaar bevraagd zonder wachttijd tussen de verzoeken. Zo kan het aantal verzoeken per minuut en de gemiddelde antwoord tijd gemeten worden.

Virtuele gebruikers
~~~~~~~~~~~~~~~~~~~

Er wordt getest met een oplopend aantal virtuele gebruikers, van 1 tot 100, die tegelijk de functionele scenario's aan het uitvoeren zijn. Een virtuele gebruiker is technisch gezien een script dat de verschillende scenario's achter elkaar uitvoert. Zo wordt inzichtelijk gemaakt wat de impact is van het aantal virtuele gebruikers op de performance.

Testdata
~~~~~~~~

De volgende test data wordt gebruikt om een realistische dataset te simuleren:

* 1.000.000 zaken in de Zaken API
* 1.000.000 documenten in de Documenten API
* 1.000.000 besluiten in de Besluiten API
* 1 catalogus met 100 zaaktypen in de Catalogi API

De volledige testset is beschreven in de technische bijlage.

Functionele test scenario's
===========================

Het testen van performance wordt gedaan door de API's zo te benaderen alsof deze gebruikt worden door een applicatie, ofwel een virtueel systeem. Er zijn enkele typische functionele scenario's geschetst vanuit de praktijk:

1. Zaken overzicht opvragen
2. Zaken overzicht opvragen van specifiek zaaktype
3. Zaken zoeken op locatie
4. Zaken zoeken op persoon
5. Zaak details opvragen
6. Geschiedenis opvragen
7. Zaak aanmaken
8. Status toevoegen
9. Betrokkene toevoegen
10. Document toevoegen
11. Besluit toevoegen
12. Resultaat toevoegen

Scenario's in API-verzoeken
---------------------------

Alle functionele scenario's zijn vertaald naar API-verzoeken. Het aantal API-verzoeken, de exacte query parameters voor het filteren en/of sorteren van lijsten, en de gegevens die worden verstuurd voor het aanmaken van objecten, zijn allemaal zeer dynamisch in de praktijk. Er wordt voor elk functioneel scenario een of meerdere concrete API verzoeken opgesteld die het scenario zo goed mogelijk invullen.

Enkele API-verzoeken zijn buiten scope geplaatst omdat ze geen onderdeel zijn van API's voor Zaakgericht werken maar hoogstwaarschijnlijk wel nodig zijn om een functionele gebruikersinterface op te bouwen.

Zaken overzicht opvragen (1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Een ongefilterde lijst van zaken opvragen, samen met hun zaaktype en statustype.

**Zaken API**

* 1x ZAAKen opvragen (``GET /api/v1/zaken``)
* 1x STATUSsen opvragen (``GET /api/v1/statussen``)

**Catalogi API**

* 1x ZAAKTYPEn opvragen (``GET /api/v1/zaaktypen``)
* 1x STATUSTYPEn opvragen (``GET /api/v1/statustypen``)

Zaken overzicht opvragen van specifiek zaaktype (2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Een gefilterde lijst van zaken opvragen, samen met hun zaaktype en statustype. Alle statussen worden opgevraagd gefiltered op de 3 beschikbare statustypen voor het betreffende zaaktype.

**Zaken API**

* 1x ZAAKen opvragen (``GET /api/v1/zaken?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 3x STATUSsen opvragen (``GET /api/v1/statussen?statustype=/api/v1/statustypen/f82..396``)

**Catalogi API**

* 1x ZAAKTYPEn opvragen (``GET /api/v1/zaaktypen/011..3c1``)
* 1x STATUSTYPEn opvragen (``GET /api/v1/statustypen?zaaktype=/api/v1/zaaktypen/011..3c1``)

Zaken zoeken op locatie (3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Een lijst van zaken opvragen die raakvlak hebben met een bepaald geografisch gebied (polygon).

**Zaken API**

* 1x ZAAKen zoeken (``POST /api/v1/zaken/_zoek``)

Zaken zoeken op persoon (4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Een lijst van zaken opvragen met een specifieke betrokkene bij die zaken.

* *1x Betrokkene zoeken (buiten scope)*

**Zaken API**

* 1x ZAAKen filteren ``GET /api/v1/rollen?betrokkene=https://personen/api/v1/a66c38``

Zaak details opvragen (5)
~~~~~~~~~~~~~~~~~~~~~~~~~

Een afgeronde enkele zaak opvragen, met een resultaat, een besluit, *2 zaakobjecten*, *3 betrokkenen* en 3 documenten.

* *3x Betrokkenen opvragen via ROLlen-resultaat (buiten scope)*
* *2x Objecten opvragen via ZAAKOBJECTen-resultaat (buiten scope)*

**Zaken API**

* 1x ZAAK opvragen (``GET /api/v1/zaken/d4d..2e8``)
* 1x STATUSsen opvragen (``GET /api/v1/statussen?zaak=/api/v1/zaken/d4d..2e8``)
* 1x RESULTAAT opvragen (``GET /api/v1/resultaten/f84..e9e``)
* 1x ROLlen opvragen (``GET /api/v1/rollen?zaak=/api/v1/zaken/d4d..2e8``)
* 1x ZAAKOBJECTen opvragen (``GET /api/v1/zaakobjecten?zaak=/api/v1/zaken/d4d..2e8``)

**Catalogi API**

* 1x ZAAKTYPE opvragen (``GET /api/v1/zaaktypen/011..3c1``)
* 1x STATUSTYPEn opvragen (``GET /api/v1/statustypen?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 1x BESLUITTYPE opvragen (``GET /api/v1/besluittypen?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 1x RESULTAATTYPE opvragen (``GET /api/v1/resultaattypen/712..a7c?zaaktype=/api/v1/zaaktypen/011..3c1``)

**Documenten API**

* 1x OBJECTINFORMATIEOBJECTen opvragen (``GET /api/v1/objectinformatieobjecten?object=/api/v1/zaken/d4d..2e8``)
* 3x ENKELVOUDIGINFORMATIEOBJECT opvragen (``GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90``)

**Besluiten API**

* 1x BESLUITen opvragen (``GET /api/v1/besluiten?zaak=/api/v1/zaken/d4d..2e8``)

Geschiedenis opvragen (6)
~~~~~~~~~~~~~~~~~~~~~~~~~

De gecombineerde audit trail opvragen van een zaak, een besluit en 3 documenten uit hun respectievelijke API's.

**Zaken API**

* 1x AUDITTRAIL opvragen (``GET /api/v1/zaken/d4d..2e8/audittrail``)

**Documenten API**

* 3x AUDITTRAIL opvragen (``GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90/audittrail``)

**Besluiten API**

* 1x AUDITTRAIL opvragen (``GET /api/v1/besluiten/a28..6d3/audittrail``)

Zaak aanmaken (7)
~~~~~~~~~~~~~~~~~

Een zaak aanmaken met een initiële status en een initiator.

**Zaken API**

* 1x ZAAK aanmaken (``POST /api/v1/zaken``)
* 1x STATUS aanmaken (``POST /api/v1/status``)
* 1x ROL aanmaken (``POST /api/v1/rollen``)

Status toevoegen (8)
~~~~~~~~~~~~~~~~~~~~

**Zaken API**

* 1x STATUS aanmaken (``POST /api/v1/status``)

Betrokkene toevoegen (9)
~~~~~~~~~~~~~~~~~~~~~~~~

* *1x Persoon zoeken (buiten scope)*

**Zaken API**

* 1x ROL aanmaken (``POST /api/v1/rollen``)

Document toevoegen (10)
~~~~~~~~~~~~~~~~~~~~~~~

Een document aanmaken en de relatie leggen met een zaak.

**Zaken API**

* 1x ZAAK-INFORMATIEOBJECT aanmaken (``POST /api/v1/zaakinformatieobjecten``)

**Documenten API**

* 1x ENKELVOUDIGINFORMATIEOBJECT aanmaken (``POST /api/v1/enkelvoudiginformatieobjecten``)

Besluit toevoegen (11)
~~~~~~~~~~~~~~~~~~~~~~

**Besluiten API**

* 1x BESLUIT aanmaken (``POST /api/v1/besluiten``)

Resultaat toevoegen (12)
~~~~~~~~~~~~~~~~~~~~~~~~

**Zaken API**

* 1x RESULTAAT aanmaken (``POST /api/v1/resultaten``)

Test specificatie
-----------------

Gebruik van scenario's
~~~~~~~~~~~~~~~~~~~~~~

Niet elk scenario wordt even vaak uitgevoerd. Een zaak wordt bijvoorbeeld vaker opgevraagd dan aangemaakt. In de onderstaande tabel wordt bijvoorbeeld voor elke 20x "Zaken overzicht opvragen", 10x "Zaak aanmaken" uitgevoerd. Vervolgens is dit omgezet naar een percentage, er van uitgaande dat alle scenario's 100% vertegenwoordigt.

Om de praktijk verder te benaderen wordt voor elk scenario een bepaalde wachttijd genomen. De wachttijd is de tijd die een echte gebruiker bijvoorbeeld nodig heeft om gegevens in te vullen in de gebruikersinterface. Deze wachttijd vertaald zich naar de tijd tussen scenario's. In de onderstaande tabel wordt bijvoorbeeld bij het uitvoeren van "Zaak aanmaken" eerst tussen 0 en 10 minuten gewacht (gemiddeld 5 minuten).

De wachttijd staat voor de snelheid waarmee gebruikers bepaalde acties in het virtuele systeem uitvoeren en daarmee de belasting die ze veroorzaken.

=== ==============================  ======  ======  ======  ======
#   Scenario                        Verdeling       Wachttijd (m)
--- ------------------------------  --------------  --------------
.   .                               Abs.    %       Avg.    Range
=== ==============================  ======  ======  ======  ======
1   Zaken overzicht opvragen        20      20%     2.5     0 - 5
2   ... voor specifiek zaaktype     10      10%     2.5     0 - 5
3   Zaken zoeken op locatie         1       1%      2.5     0 - 5
4   Zaken zoeken op persoon         10      10%     2.5     0 - 5
5   Zaak details opvragen           8       8%      2.5     0 - 5
6   Geschiedenis opvragen           2       2%      2.5     0 - 5
7   Zaak aanmaken                   10      10%     2.5     0 - 5
8   Status toevoegen                20      20%     2.5     0 - 5
9   Betrokkene toevoegen            3       3%      2.5     0 - 5
10  Document toevoegen              12      12%     2.5     0 - 5
11  Besluit toevoegen               2       2%      2.5     0 - 5
12  Resultaat toevoegen             2       2%      2.5     0 - 5
.   **Totaal**                      100     100%
=== ==============================  ======  ======  ======  ======

Virtuele gebruikers
~~~~~~~~~~~~~~~~~~~

Er wordt getest met een oplopend aantal virtuele gebruikers, van 10 tot 1000, die tegelijk de functionele scenario's aan het uitvoeren zijn. Een virtuele gebruiker is technisch gezien een script dat de verschillende scenario's uitvoert, in de genoemde verdeling en met de bijbehorende wachttijd.

Testdata
~~~~~~~~

De volgende test data wordt gebruikt om een realistische dataset te simuleren:

* 1.000.000 zaken in de Zaken API
* 1.000.000 documenten in de Documenten API
* 1.000.000 besluiten in de Besluiten API
* 1 catalogus met 100 zaaktypen in de Catalogi API
