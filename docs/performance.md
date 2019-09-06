# Performance testing

## Functionele test scenario's

Het testen van performance wordt gedaan door de API's zo te benaderen alsof deze gebruikt worden door een applicatie. Er zijn enkele typische functionele scenario's geschetst vanuit de praktijk:

* Zaken overzicht opvragen
* Zaak zoeken op locatie
* Zaak zoeken op persoon
* Zaak details opvragen
* Geschiedenis opvragen
* Zaak aanmaken
* Status toevoegen
* Betrokkene toevoegen
* Document toevoegen
* Besluit toevoegen
* Resultaat toevoegen

## Scenario's in API-verzoeken

Alle functionele scenario's zijn vertaald naar API-verzoeken. Het aantal API-verzoeken, de exacte query parameters voor het filteren en/of sorteren van lijsten, en de gegevens die worden verstuurd voor het aanmaken van objecten, zijn allemaal zeer dynamisch in de praktijk. Er wordt voor elk functioneel scenario een of meerdere concrete API verzoeken opgesteld die het scenario zo goed mogelijk invullen.

### Zaken overzicht opvragen

Een ongefilterde lijst van zaken opvragen, samen met hun zaaktype en statustype.

**Zaken API**

TODO: Filter on closed/open or order by date?

* 1x ZAAKen opvragen (`GET /api/v1/zaken/`)
* 1x STATUSsen opvragen (`GET /api/v1/statussen`)

**Catalogi API**

* 1x ZAAKTYPE opvragen (`GET /api/v1/zaaktypen`)
* 1x STATUSTYPEn opvragen (`GET /api/v1/statustypen`)

### Zaak zoeken op locatie

TODO

### Zaak zoeken op persoon

TODO

### Zaak details opvragen

Een afgeronde enkele zaak opvragen, met een resultaat, een besluit, 2 zaakobjecten, 3 betrokkenen en 3 documenten.

**Zaken API**

* 1x ZAAK opvragen (`GET /api/v1/zaken/d4d..2e8`)
* 1x STATUSsen opvragen (`GET /api/v1/statussen?zaak=/api/v1/zaken/d4d..2e8`)
* 1x RESULTAAT (`GET /api/v1/resultaten/f84..e9e`)
* 1x ROLlen (`GET /api/v1/rollen?zaak=/api/v1/zaken/d4d..2e8`)
* 3x BETROKKENE (`GET ...`)
* 1x ZAAKOBJECTen (`GET /api/v1/zaakobjecten?zaak=/api/v1/zaken/d4d..2e8`)
* 2x OBJECT (`GET ...`)

**Catalogi API**

TODO: Filter beforehand on ZAAKTYPE?

* 1x ZAAKTYPE opvragen (`GET /api/v1/zaaktypen/011..3c1`)
* 1x STATUSTYPEn opvragen (`GET /api/v1/statustypen`)
* 1x BESLUITTYPE opvragen (`GET /api/v1/besluittypen`)
* 1x RESULTAATTYPE (`GET /api/v1/resultaattypen/712..a7c`)

**Documenten API**

* 1x OBJECTINFORMATIEOBJECTen opvragen (`GET /api/v1/objectinformatieobjecten?object=/api/v1/zaken/d4d..2e8`)
* 3x ENKELVOUDIGINFORMATIEOBJECT opvragen (`GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90`)

**Besluiten API**

* 1x BESLUITen opvragen (`GET /api/v1/besluiten?zaak=/api/v1/zaken/d4d..2e8`)

### Geschiedenis opvragen

De gecombineerde audit trail opvragen van een zaak, een besluit en 3 documenten uit hun respectievelijke API's.

**Zaken API**

* 1x AUDITTRAIL (`GET /api/v1/zaken/d4d..2e8/audittrail`)

**Documenten API**

* 3x AUDITTRAIL (`GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90/audittrail`)

**Besluiten API**

* 1x AUDITTRAIL (`GET /api/v1/besluiten/a28..6d3/audittrail`)

### Zaak aanmaken

TODO

### Status toevoegen

TODO

### Betrokkene toevoegen

TODO

### Document toevoegen

TODO

### Besluit toevoegen

TODO

### Resultaat toevoegen

TODO

## Test specificatie

### Verdeling van scenario's

Niet elk scenario wordt even vaak uitgevoerd. Een zaak wordt bijvoorbeeld vaker opgevraagd dan aangemaakt. Als we dit voorbeeld bekijken wordt voor elk 20x "Zaken overzicht opvragen" 10x "Zaak aanmaken" uitgevoerd. Vervolgens is dit omgezet naar een percentage, uitgaande van 100%. Hieronder staat de aangehouden verdeling.

| Scenario | Verdeling | Verdeling % |
|---|---|---|
| Zaken overzicht opvragen | 20 | 22% |
| Zaak zoeken op locatie | 10| 11% |
| Zaak zoeken op persoon | 10 | 11% |
| Zaak details opvragen | 8 | 9% |
| Geschiedenis opvragen | 2 | 2% |
| Zaak aanmaken | 10 | 11% |
| Status toevoegen | 20 | 22% |
| Betrokkene toevoegen | 3 | 3% |
| Document toevoegen | 3 | 3% |
| Besluit toevoegen | 2 | 2% |
| Resultaat toevoegen | 2 | 2% |
| **Totaal** | 90 | 100% |

### Gebruikers

TODO
