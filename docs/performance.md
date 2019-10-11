# Performance metingen

## Doel

Het doel van de performance metingen is om inzicht te verkrijgen in de relaties tussen systeemeisen, aantal gebruikers en reactiesnelheid van de API's. Uit deze relaties kunnen we de minimum systeemeisen opstellen, afhankelijk van het aantal gebruikers, waarop de API's nog acceptabel presteren.

Tevens maakt een gestandardiseerde performance meting inzichtelijk welke effect optimalisaties hebben, zodat er doelgericht en aantoonbaar verbeteringen kunnen worden doorgevoerd.

## Functionele test scenario's

Het testen van performance wordt gedaan door de API's zo te benaderen alsof deze gebruikt worden door een applicatie. Er zijn enkele typische functionele scenario's geschetst vanuit de praktijk:

1. Zaken overzicht opvragen
2. Zaken zoeken op locatie
3. Zaken zoeken op persoon
4. Zaak details opvragen
5. Geschiedenis opvragen
6. Zaak aanmaken
7. Status toevoegen
8. Betrokkene toevoegen
9. Document toevoegen
10. Besluit toevoegen
11. Resultaat toevoegen

## Scenario's in API-verzoeken

Alle functionele scenario's zijn vertaald naar API-verzoeken. Het aantal API-verzoeken, de exacte query parameters voor het filteren en/of sorteren van lijsten, en de gegevens die worden verstuurd voor het aanmaken van objecten, zijn allemaal zeer dynamisch in de praktijk. Er wordt voor elk functioneel scenario een of meerdere concrete API verzoeken opgesteld die het scenario zo goed mogelijk invullen.

Enkele API-verzoeken zijn buiten scope geplaatst omdat ze geen onderdeel zijn van API's voor Zaakgericht werken maar hoogstwaarschijnlijk wel nodig zijn om een functionele gebruikersinterface op te bouwen.

### Zaken overzicht opvragen (1)

Een ongefilterde lijst van zaken opvragen, samen met hun zaaktype en statustype.

**Zaken API**

* 1x ZAAKen opvragen (`GET /api/v1/zaken/`)
* 1x STATUSsen opvragen (`GET /api/v1/statussen`)

**Catalogi API**

* 1x ZAAKTYPE opvragen (`GET /api/v1/zaaktypen`)
* 1x STATUSTYPEn opvragen (`GET /api/v1/statustypen`)

### Zaken zoeken op locatie (2)

Een lijst van zaken opvragen die raakvlak hebben met een bepaald geografisch gebied (polygon).

**Zaken API**

* 1x ZAAKen zoeken (`POST /api/v1/zaken/_zoek`)

### Zaken zoeken op persoon (3)

Een lijst van zaken opvragen met een specifieke betrokkene bij die zaken.

* *1x Betrokkene zoeken (buiten scope)*

**Zaken API**

* 1x ZAAKen filteren `GET /api/v1/rollen?betrokkene=https://personen/api/v1/a66c38`

### Zaak details opvragen (4)

Een afgeronde enkele zaak opvragen, met een resultaat, een besluit, *2 zaakobjecten*, *3 betrokkenen* en 3 documenten.

* *3x Betrokkenen opvragen via ROLlen-resultaat (buiten scope)*
* *2x Objecten opvragen via ZAAKOBJECTen-resultaat (buiten scope)*

**Zaken API**

* 1x ZAAK opvragen (`GET /api/v1/zaken/d4d..2e8`)
* 1x STATUSsen opvragen (`GET /api/v1/statussen?zaak=/api/v1/zaken/d4d..2e8`)
* 1x RESULTAAT opvragen (`GET /api/v1/resultaten/f84..e9e`)
* 1x ROLlen opvragen (`GET /api/v1/rollen?zaak=/api/v1/zaken/d4d..2e8`)
* 1x ZAAKOBJECTen opvragen (`GET /api/v1/zaakobjecten?zaak=/api/v1/zaken/d4d..2e8`)

**Catalogi API**

* 1x ZAAKTYPE opvragen (`GET /api/v1/zaaktypen/011..3c1`)
* 1x STATUSTYPEn opvragen (`GET /api/v1/statustypen?zaaktype=/api/v1/zaaktypen/011..3c1`)
* 1x BESLUITTYPE opvragen (`GET /api/v1/besluittypen?zaaktype=/api/v1/zaaktypen/011..3c1`)
* 1x RESULTAATTYPE opvragen (`GET /api/v1/resultaattypen/712..a7c?zaaktype=/api/v1/zaaktypen/011..3c1`)

**Documenten API**

* 1x OBJECTINFORMATIEOBJECTen opvragen (`GET /api/v1/objectinformatieobjecten?object=/api/v1/zaken/d4d..2e8`)
* 3x ENKELVOUDIGINFORMATIEOBJECT opvragen (`GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90`)

**Besluiten API**

* 1x BESLUITen opvragen (`GET /api/v1/besluiten?zaak=/api/v1/zaken/d4d..2e8`)

### Geschiedenis opvragen (5)

De gecombineerde audit trail opvragen van een zaak, een besluit en 3 documenten uit hun respectievelijke API's.

**Zaken API**

* 1x AUDITTRAIL opvragen (`GET /api/v1/zaken/d4d..2e8/audittrail`)

**Documenten API**

* 3x AUDITTRAIL opvragen (`GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90/audittrail`)

**Besluiten API**

* 1x AUDITTRAIL opvragen (`GET /api/v1/besluiten/a28..6d3/audittrail`)

### Zaak aanmaken (6)

Een zaak aanmaken

**Zaken API**

* 1x ZAAK aanmaken (`POST /api/v1/zaken`)
* 1x STATUS aanmaken (`POST /api/v1/status`)
* 1x ROL aanmaken (`POST /api/v1/rollen`)

### Status toevoegen (7)

**Zaken API**

* 1x STATUS aanmaken (`POST /api/v1/status`)

### Betrokkene toevoegen (8)

* *1x Persoon zoeken (buiten scope)*

**Zaken API**

* 1x ROL aanmaken (`POST /api/v1/rollen`)

### Document toevoegen (9)

**Zaken API**

* 1x ZAAK-INFORMATIEOBJECT aanmaken (`POST /api/v1/zaakinformatieobjecten`)

**Documenten API**

* 1x ENKELVOUDIGINFORMATIEOBJECT aanmaken (`POST /api/v1/enkelvoudiginformatieobjecten`)

### Besluit toevoegen (10)

**Besluiten API**

* 1x BESLUIT aanmaken (`POST /api/v1/besluiten`)

### Resultaat toevoegen (11)

**Zaken API**

* 1x RESULTAAT aanmaken (`POST /api/v1/resultaten`)

## Test specificatie

### Verdeling van scenario's

Niet elk scenario wordt even vaak uitgevoerd. Een zaak wordt bijvoorbeeld vaker opgevraagd dan aangemaakt. Als we dit voorbeeld bekijken wordt voor elke 20x "Zaken overzicht opvragen", 10x "Zaak aanmaken" uitgevoerd. Vervolgens is dit omgezet naar een percentage, uitgaande van 100%. Hieronder staat de aangehouden verdeling.

| # | Scenario | Verdeling | Verdeling % |
|---|---|---|---|
| 1 | Zaken overzicht opvragen | 20 | 22% |
| 2 | Zaken zoeken op locatie | 10| 11% |
| 3 | Zaken zoeken op persoon | 10 | 11% |
| 4 | Zaak details opvragen | 8 | 9% |
| 5 | Geschiedenis opvragen | 2 | 2% |
| 6 | Zaak aanmaken | 10 | 11% |
| 7 | Status toevoegen | 20 | 22% |
| 8 | Betrokkene toevoegen | 3 | 3% |
| 9 | Document toevoegen | 3 | 3% |
| 10 | Besluit toevoegen | 2 | 2% |
| 11 | Resultaat toevoegen | 2 | 2% |
| | **Totaal** | 90 | 100% |

### Gebruikers en gebruik

TODO: Iets met klikpaden?

### Testdata

De volgende test data wordt gebruikt om een realistische dataset te simuleren:

* 1.000.000 zaken in de Zaken API
* 1.000.000 documenten in de Documenten API
* 1.000.000 besluiten in de Besluiten API
* 1 catalogus met 100 zaaktypen in de Catalogi API

De volledige testset is beschreven in de technische bijlage.
