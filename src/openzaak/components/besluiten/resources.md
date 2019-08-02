# Resources

Dit document beschrijft de (RGBZ-)objecttypen die als resources ontsloten
worden met de beschikbare attributen.


## Besluit

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/besluit)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| identificatie | Identificatie van het besluit binnen de organisatie die het besluit heeft vastgesteld. Indien deze niet opgegeven is, dan wordt die gegenereerd. | string | nee | C​R​U​D |
| verantwoordelijkeOrganisatie | Het RSIN van de niet-natuurlijk persoon zijnde de organisatie die het besluit heeft vastgesteld. | string | ja | C​R​U​D |
| besluittype | URL-referentie naar het BESLUITTYPE (in de Catalogi API). | string | ja | C​R​U​D |
| zaak | URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is. | string | nee | C​R​U​D |
| datum | De beslisdatum (AWB) van het besluit. | string | ja | C​R​U​D |
| toelichting | Toelichting bij het besluit. | string | nee | C​R​U​D |
| bestuursorgaan | Een orgaan van een rechtspersoon krachtens publiekrecht ingesteld of een persoon of college, met enig openbaar gezag bekleed onder wiens verantwoordelijkheid het besluit vastgesteld is. | string | nee | C​R​U​D |
| ingangsdatum | Ingangsdatum van de werkingsperiode van het besluit. | string | ja | C​R​U​D |
| vervaldatum | Datum waarop de werkingsperiode van het besluit eindigt. | string | nee | C​R​U​D |
| vervalreden | De omschrijving die aangeeft op grond waarvan het besluit is of komt te vervallen.

Uitleg bij mogelijke waarden:

* `tijdelijk` - Besluit met tijdelijke werking
* `ingetrokken_overheid` - Besluit ingetrokken door overheid
* `ingetrokken_belanghebbende` - Besluit ingetrokken o.v.v. belanghebbende | string | nee | C​R​U​D |
| vervalredenWeergave |  | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| publicatiedatum | Datum waarop het besluit gepubliceerd wordt. | string | nee | C​R​U​D |
| verzenddatum | Datum waarop het besluit verzonden is. | string | nee | C​R​U​D |
| uiterlijkeReactiedatum | De datum tot wanneer verweer tegen het besluit mogelijk is. | string | nee | C​R​U​D |

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

## BesluitInformatieObject

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/besluitinformatieobject)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| informatieobject | URL-referentie naar het INFORMATIEOBJECT (in de Documenten API) waarin (een deel van) het besluit beschreven is. | string | ja | C​R​U​D |
| besluit | URL-referentie naar het BESLUIT. | string | ja | C​R​U​D |


* Create, Read, Update, Delete
