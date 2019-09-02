# Resources

Dit document beschrijft de (RGBZ-)objecttypen die als resources ontsloten
worden met de beschikbare attributen.


## EnkelvoudigInformatieObject

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/enkelvoudiginformatieobject)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| identificatie | Een binnen een gegeven context ondubbelzinnige referentie naar het INFORMATIEOBJECT. | string | nee | C​R​U​D |
| bronorganisatie | Het RSIN van de Niet-natuurlijk persoon zijnde de organisatie die het informatieobject heeft gecreëerd of heeft ontvangen en als eerste in een samenwerkingsketen heeft vastgelegd. | string | ja | C​R​U​D |
| creatiedatum | Een datum of een gebeurtenis in de levenscyclus van het INFORMATIEOBJECT. | string | ja | C​R​U​D |
| titel | De naam waaronder het INFORMATIEOBJECT formeel bekend is. | string | ja | C​R​U​D |
| vertrouwelijkheidaanduiding | Aanduiding van de mate waarin het INFORMATIEOBJECT voor de openbaarheid bestemd is.

Uitleg bij mogelijke waarden:

* `openbaar` - Openbaar
* `beperkt_openbaar` - Beperkt openbaar
* `intern` - Intern
* `zaakvertrouwelijk` - Zaakvertrouwelijk
* `vertrouwelijk` - Vertrouwelijk
* `confidentieel` - Confidentieel
* `geheim` - Geheim
* `zeer_geheim` - Zeer geheim | string | nee | C​R​U​D |
| auteur | De persoon of organisatie die in de eerste plaats verantwoordelijk is voor het creëren van de inhoud van het INFORMATIEOBJECT. | string | ja | C​R​U​D |
| status | Aanduiding van de stand van zaken van een INFORMATIEOBJECT. De waarden &#39;in bewerking&#39; en &#39;ter vaststelling&#39; komen niet voor als het attribuut `ontvangstdatum` van een waarde is voorzien. Wijziging van de Status in &#39;gearchiveerd&#39; impliceert dat het informatieobject een duurzaam, niet-wijzigbaar Formaat dient te hebben.

Uitleg bij mogelijke waarden:

* `in_bewerking` - (In bewerking) Aan het informatieobject wordt nog gewerkt.
* `ter_vaststelling` - (Ter vaststelling) Informatieobject gereed maar moet nog vastgesteld worden.
* `definitief` - (Definitief) Informatieobject door bevoegd iets of iemand vastgesteld dan wel ontvangen.
* `gearchiveerd` - (Gearchiveerd) Informatieobject duurzaam bewaarbaar gemaakt; een gearchiveerd informatie-element. | string | nee | C​R​U​D |
| formaat | Het &quot;Media Type&quot; (voorheen &quot;MIME type&quot;) voor de wijze waaropde inhoud van het INFORMATIEOBJECT is vastgelegd in een computerbestand. Voorbeeld: `application/msword`. Zie: https://www.iana.org/assignments/media-types/media-types.xhtml | string | nee | C​R​U​D |
| taal | Een ISO 639-2/B taalcode waarin de inhoud van het INFORMATIEOBJECT is vastgelegd. Voorbeeld: `nld`. Zie: https://www.iso.org/standard/4767.html | string | ja | C​R​U​D |
| versie | Het (automatische) versienummer van het INFORMATIEOBJECT. Deze begint bij 1 als het INFORMATIEOBJECT aangemaakt wordt. | integer | nee | ~~C~~​R​~~U~~​~~D~~ |
| beginRegistratie | Een datumtijd in ISO8601 formaat waarop deze versie van het INFORMATIEOBJECT is aangemaakt of gewijzigd. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| bestandsnaam | De naam van het fysieke bestand waarin de inhoud van het informatieobject is vastgelegd, inclusief extensie. | string | nee | C​R​U​D |
| inhoud | Download URL van de binaire inhoud. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| bestandsomvang | Aantal bytes dat de inhoud van INFORMATIEOBJECT in beslag neemt. | integer | nee | ~~C~~​R​~~U~~​~~D~~ |
| link | De URL waarmee de inhoud van het INFORMATIEOBJECT op te vragen is. | string | nee | C​R​U​D |
| beschrijving | Een generieke beschrijving van de inhoud van het INFORMATIEOBJECT. | string | nee | C​R​U​D |
| ontvangstdatum | De datum waarop het INFORMATIEOBJECT ontvangen is. Verplicht te registreren voor INFORMATIEOBJECTen die van buiten de zaakbehandelende organisatie(s) ontvangen zijn. Ontvangst en verzending is voorbehouden aan documenten die van of naar andere personen ontvangen of verzonden zijn waarbij die personen niet deel uit maken van de behandeling van de zaak waarin het document een rol speelt. | string | nee | C​R​U​D |
| verzenddatum | De datum waarop het INFORMATIEOBJECT verzonden is, zoals deze op het INFORMATIEOBJECT vermeld is. Dit geldt voor zowel inkomende als uitgaande INFORMATIEOBJECTen. Eenzelfde informatieobject kan niet tegelijk inkomend en uitgaand zijn. Ontvangst en verzending is voorbehouden aan documenten die van of naar andere personen ontvangen of verzonden zijn waarbij die personen niet deel uit maken van de behandeling van de zaak waarin het document een rol speelt. | string | nee | C​R​U​D |
| indicatieGebruiksrecht | Indicatie of er beperkingen gelden aangaande het gebruik van het informatieobject anders dan raadpleging. Dit veld mag `null` zijn om aan te geven dat de indicatie nog niet bekend is. Als de indicatie gezet is, dan kan je de gebruiksrechten die van toepassing zijn raadplegen via de GEBRUIKSRECHTen resource. | boolean | nee | C​R​U​D |
| informatieobjecttype | URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API). | string | ja | C​R​U​D |
| locked | Geeft aan of het document gelocked is. Alleen als een document gelocked is, mogen er aanpassingen gemaakt worden. | boolean | nee | ~~C~~​R​~~U~~​~~D~~ |

## AuditTrail

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/audittrail)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| uuid | Unieke identificatie van de audit regel. | string | nee | C​R​U​D |
| bron | De naam van het component waar de wijziging in is gedaan.

Uitleg bij mogelijke waarden:

* `ac` - Autorisatiecomponent
* `nrc` - Notificatierouteringcomponent
* `zrc` - Zaakregistratiecomponent
* `ztc` - Zaaktypecatalogus
* `drc` - Documentregistratiecomponent
* `brc` - Besluitregistratiecomponent | string | ja | C​R​U​D |
| applicatieId | Unieke identificatie van de applicatie, binnen de organisatie. | string | nee | C​R​U​D |
| applicatieWeergave | Vriendelijke naam van de applicatie. | string | nee | C​R​U​D |
| gebruikersId | Unieke identificatie van de gebruiker die binnen de organisatie herleid kan worden naar een persoon. | string | nee | C​R​U​D |
| gebruikersWeergave | Vriendelijke naam van de gebruiker. | string | nee | C​R​U​D |
| actie | De uitgevoerde handeling.

De bekende waardes voor dit veld zijn hieronder aangegeven,                         maar andere waardes zijn ook toegestaan

Uitleg bij mogelijke waarden:

* `create` - Object aangemaakt
* `list` - Lijst van objecten opgehaald
* `retrieve` - Object opgehaald
* `destroy` - Object verwijderd
* `update` - Object bijgewerkt
* `partial_update` - Object deels bijgewerkt | string | ja | C​R​U​D |
| actieWeergave | Vriendelijke naam van de actie. | string | nee | C​R​U​D |
| resultaat | HTTP status code van de API response van de uitgevoerde handeling. | integer | ja | C​R​U​D |
| hoofdObject | De URL naar het hoofdobject van een component. | string | ja | C​R​U​D |
| resource | Het type resource waarop de actie gebeurde. | string | ja | C​R​U​D |
| resourceUrl | De URL naar het object. | string | ja | C​R​U​D |
| toelichting | Toelichting waarom de handeling is uitgevoerd. | string | nee | C​R​U​D |
| resourceWeergave | Vriendelijke identificatie van het object. | string | ja | C​R​U​D |
| aanmaakdatum | De datum waarop de handeling is gedaan. | string | nee | ~~C~~​R​~~U~~​~~D~~ |

## Gebruiksrechten

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/gebruiksrechten)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| informatieobject | URL-referentie naar het INFORMATIEOBJECT. | string | ja | C​R​U​D |
| startdatum | Begindatum van de periode waarin de gebruiksrechtvoorwaarden van toepassing zijn. Doorgaans is de datum van creatie van het informatieobject de startdatum. | string | ja | C​R​U​D |
| einddatum | Einddatum van de periode waarin de gebruiksrechtvoorwaarden van toepassing zijn. | string | nee | C​R​U​D |
| omschrijvingVoorwaarden | Omschrijving van de van toepassing zijnde voorwaarden aan het gebruik anders dan raadpleging | string | ja | C​R​U​D |

## ObjectInformatieObject

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/objectinformatieobject)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| informatieobject | URL-referentie naar het INFORMATIEOBJECT. | string | ja | C​R​U​D |
| object | URL-referentie naar het gerelateerde OBJECT (in deze of een andere API). | string | ja | C​R​U​D |
| objectType | Het type van het gerelateerde OBJECT.

Uitleg bij mogelijke waarden:

* `besluit` - Besluit
* `zaak` - Zaak | string | ja | C​R​U​D |


* Create, Read, Update, Delete
