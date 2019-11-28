# Resources

Dit document beschrijft de (RGBZ-)objecttypen die als resources ontsloten
worden met de beschikbare attributen.


## BesluitType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/besluittype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| catalogus | URL-referentie naar de CATALOGUS waartoe dit BESLUITTYPE behoort. | string | ja | C​R​U​D |
| zaaktypen | ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit BESLUITTYPE | array | ja | C​R​U​D |
| omschrijving | Omschrijving van de aard van BESLUITen van het BESLUITTYPE. | string | nee | C​R​U​D |
| omschrijvingGeneriek | Algemeen gehanteerde omschrijving van de aard van BESLUITen van het BESLUITTYPE | string | nee | C​R​U​D |
| besluitcategorie | Typering van de aard van BESLUITen van het BESLUITTYPE. | string | nee | C​R​U​D |
| reactietermijn | De duur (typisch een aantal dagen), gerekend vanaf de verzend- of publicatiedatum, waarbinnen verweer tegen een besluit van het besluittype mogelijk is. | string | nee | C​R​U​D |
| publicatieIndicatie | Aanduiding of BESLUITen van dit BESLUITTYPE gepubliceerd moeten worden. | boolean | ja | C​R​U​D |
| publicatietekst | De generieke tekst van de publicatie van BESLUITen van dit BESLUITTYPE | string | nee | C​R​U​D |
| publicatietermijn | De duur (typisch een aantal dagen), gerekend vanaf de verzend- of publicatiedatum, dat BESLUITen van dit BESLUITTYPE gepubliceerd moeten blijven. | string | nee | C​R​U​D |
| toelichting | Een eventuele toelichting op dit BESLUITTYPE. | string | nee | C​R​U​D |
| informatieobjecttypen | URL-referenties naar het INFORMATIEOBJECTTYPE van informatieobjecten waarin besluiten van dit BESLUITTYPE worden vastgelegd. | array | ja | C​R​U​D |
| beginGeldigheid | De datum waarop het is ontstaan. | string | ja | C​R​U​D |
| eindeGeldigheid | De datum waarop het is opgeheven. | string | nee | C​R​U​D |
| concept | Geeft aan of het object een concept betreft. Concepten zijn niet-definitieve versies en zouden niet gebruikt moeten worden buiten deze API. | boolean | nee | ~~C~~​R​~~U~~​~~D~~ |

## Catalogus

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/catalogus)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| domein | Een afkorting waarmee wordt aangegeven voor welk domein in een CATALOGUS ZAAKTYPEn zijn uitgewerkt. | string | ja | C​R​U​D |
| rsin | Het door een kamer toegekend uniek nummer voor de INGESCHREVEN NIET-NATUURLIJK PERSOON die de eigenaar is van een CATALOGUS. | string | ja | C​R​U​D |
| contactpersoonBeheerNaam | De naam van de contactpersoon die verantwoordelijk is voor het beheer van de CATALOGUS. | string | ja | C​R​U​D |
| contactpersoonBeheerTelefoonnummer | Het telefoonnummer van de contactpersoon die verantwoordelijk is voor het beheer van de CATALOGUS. | string | nee | C​R​U​D |
| contactpersoonBeheerEmailadres | Het emailadres van de contactpersoon die verantwoordelijk is voor het beheer van de CATALOGUS. | string | nee | C​R​U​D |
| zaaktypen | URL-referenties naar ZAAKTYPEn die in deze CATALOGUS worden ontsloten. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| besluittypen | URL-referenties naar BESLUITTYPEn die in deze CATALOGUS worden ontsloten. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| informatieobjecttypen | URL-referenties naar INFORMATIEOBJECTTYPEn die in deze CATALOGUS worden ontsloten. | array | nee | ~~C~~​R​~~U~~​~~D~~ |

## EigenschapSpecificatie

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/eigenschapspecificatie)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| groep | Benaming van het object of groepattribuut waarvan de EIGENSCHAP een inhoudelijk gegeven specificeert. | string | nee | C​R​U​D |
| formaat | Het soort tekens waarmee waarden van de EIGENSCHAP kunnen worden vastgelegd.

Uitleg bij mogelijke waarden:

* `tekst` - Tekst
* `getal` - Getal
* `datum` - Datum
* `datum_tijd` - Datum/tijd | string | ja | C​R​U​D |
| lengte | Het aantal karakters (lengte) waarmee waarden van de EIGENSCHAP worden vastgelegd. | string | ja | C​R​U​D |
| kardinaliteit | Het aantal mogelijke voorkomens van waarden van deze EIGENSCHAP bij een zaak van het ZAAKTYPE. | string | ja | C​R​U​D |
| waardenverzameling | Waarden die deze EIGENSCHAP kan hebben. | array | nee | C​R​U​D |

## Eigenschap

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/eigenschap)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| naam | De naam van de EIGENSCHAP | string | ja | C​R​U​D |
| definitie | De beschrijving van de betekenis van deze EIGENSCHAP | string | ja | C​R​U​D |
| toelichting | Een toelichting op deze EIGENSCHAP en het belang hiervan voor zaken van dit ZAAKTYPE. | string | nee | C​R​U​D |
| zaaktype | URL-referentie naar het ZAAKTYPE van de ZAAKen waarvoor deze EIGENSCHAP van belang is. | string | ja | C​R​U​D |

## InformatieObjectType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/informatieobjecttype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| catalogus | URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort. | string | ja | C​R​U​D |
| omschrijving | Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE. | string | ja | C​R​U​D |
| vertrouwelijkheidaanduiding | Aanduiding van de mate waarin informatieobjecten van dit INFORMATIEOBJECTTYPE voor de openbaarheid bestemd zijn.

Uitleg bij mogelijke waarden:

* `openbaar` - Openbaar
* `beperkt_openbaar` - Beperkt openbaar
* `intern` - Intern
* `zaakvertrouwelijk` - Zaakvertrouwelijk
* `vertrouwelijk` - Vertrouwelijk
* `confidentieel` - Confidentieel
* `geheim` - Geheim
* `zeer_geheim` - Zeer geheim | string | ja | C​R​U​D |
| beginGeldigheid | De datum waarop het is ontstaan. | string | ja | C​R​U​D |
| eindeGeldigheid | De datum waarop het is opgeheven. | string | nee | C​R​U​D |
| concept | Geeft aan of het object een concept betreft. Concepten zijn niet-definitieve versies en zouden niet gebruikt moeten worden buiten deze API. | boolean | nee | ~~C~~​R​~~U~~​~~D~~ |

## ResultaatType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/resultaattype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| zaaktype | URL-referentie naar het ZAAKTYPE van ZAAKen waarin resultaten van dit RESULTAATTYPE bereikt kunnen worden. | string | ja | C​R​U​D |
| omschrijving | Omschrijving van de aard van resultaten van het RESULTAATTYPE. | string | ja | C​R​U​D |
| resultaattypeomschrijving | Algemeen gehanteerde omschrijving van de aard van resultaten van het RESULTAATTYPE. Dit moet een URL-referentie zijn naar de referenlijst van generieke resultaattypeomschrijvingen. Im ImZTC heet dit &#39;omschrijving generiek&#39; | string | ja | C​R​U​D |
| omschrijvingGeneriek | Waarde van de omschrijving-generiek referentie (attribuut `omschrijving`) | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| selectielijstklasse | URL-referentie naar de, voor het archiefregime bij het RESULTAATTYPE relevante, categorie in de Selectielijst Archiefbescheiden (RESULTAAT in de Selectielijst API) van de voor het ZAAKTYPE verantwoordelijke overheidsorganisatie. | string | ja | C​R​U​D |
| toelichting | Een toelichting op dit RESULTAATTYPE en het belang hiervan voor ZAAKen waarin een resultaat van dit RESULTAATTYPE wordt geselecteerd. | string | nee | C​R​U​D |
| archiefnominatie | Aanduiding die aangeeft of ZAAKen met een resultaat van dit RESULTAATTYPE blijvend moeten worden bewaard of (op termijn) moeten worden vernietigd. Indien niet expliciet opgegeven wordt dit gevuld vanuit de selectielijst.

Uitleg bij mogelijke waarden:

* `blijvend_bewaren` - Het zaakdossier moet bewaard blijven en op de Archiefactiedatum overgedragen worden naar een archiefbewaarplaats.
* `vernietigen` - Het zaakdossier moet op of na de Archiefactiedatum vernietigd worden. | string | nee | C​R​U​D |
| archiefactietermijn | De termijn, na het vervallen van het bedrjfsvoeringsbelang, waarna het zaakdossier (de ZAAK met alle bijbehorende INFORMATIEOBJECTen) van een ZAAK met een resultaat van dit RESULTAATTYPE vernietigd of overgebracht (naar een archiefbewaarplaats) moet worden. Voor te vernietigen dossiers betreft het de in die Selectielijst genoemde bewaartermjn. Voor blijvend te bewaren zaakdossiers betreft het de termijn vanaf afronding van de zaak tot overbrenging (de procestermijn is dan nihil). | string | nee | C​R​U​D |

## RolType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/roltype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| zaaktype | URL-referentie naar het ZAAKTYPE waar deze ROLTYPEn betrokken kunnen zijn. | string | ja | C​R​U​D |
| omschrijving | Omschrijving van de aard van de ROL. | string | ja | C​R​U​D |
| omschrijvingGeneriek | Algemeen gehanteerde omschrijving van de aard van de ROL.

Uitleg bij mogelijke waarden:

* `adviseur` - (Adviseur) Kennis in dienst stellen van de behandeling van (een deel van) een zaak.
* `behandelaar` - (Behandelaar) De vakinhoudelijke behandeling doen van (een deel van) een zaak.
* `belanghebbende` - (Belanghebbende) Vanuit eigen en objectief belang rechtstreeks betrokken zijn bij de behandeling en/of de uitkomst van een zaak.
* `beslisser` - (Beslisser) Nemen van besluiten die voor de uitkomst van een zaak noodzakelijk zijn.
* `initiator` - (Initiator) Aanleiding geven tot de start van een zaak ..
* `klantcontacter` - (Klantcontacter) Het eerste aanspreekpunt zijn voor vragen van burgers en bedrijven ..
* `zaakcoordinator` - (Zaakcoördinator) Er voor zorg dragen dat de behandeling van de zaak in samenhang uitgevoerd wordt conform de daarover gemaakte afspraken.
* `mede_initiator` - Mede-initiator | string | ja | C​R​U​D |

## StatusType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/statustype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| omschrijving | Een korte, voor de initiator van de zaak relevante, omschrijving van de aard van de STATUS van zaken van een ZAAKTYPE. | string | ja | C​R​U​D |
| omschrijvingGeneriek | Algemeen gehanteerde omschrijving van de aard van STATUSsen van het STATUSTYPE | string | nee | C​R​U​D |
| statustekst | De tekst die wordt gebruikt om de Initiator te informeren over het bereiken van een STATUS van dit STATUSTYPE bij het desbetreffende ZAAKTYPE. | string | nee | C​R​U​D |
| zaaktype | URL-referentie naar het ZAAKTYPE van ZAAKen waarin STATUSsen van dit STATUSTYPE bereikt kunnen worden. | string | ja | C​R​U​D |
| volgnummer | Een volgnummer voor statussen van het STATUSTYPE binnen een zaak. | integer | ja | C​R​U​D |
| isEindstatus | Geeft aan dat dit STATUSTYPE een eindstatus betreft. Dit gegeven is afgeleid uit alle STATUSTYPEn van dit ZAAKTYPE met het hoogste volgnummer. | boolean | nee | ~~C~~​R​~~U~~​~~D~~ |
| informeren | Aanduiding die aangeeft of na het zetten van een STATUS van dit STATUSTYPE de Initiator moet worden geïnformeerd over de statusovergang. | boolean | nee | C​R​U​D |

## ZaakTypeInformatieObjectType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/zaaktypeinformatieobjecttype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| zaaktype | URL-referentie naar het ZAAKTYPE. | string | ja | C​R​U​D |
| informatieobjecttype | URL-referentie naar het INFORMATIEOBJECTTYPE. | string | ja | C​R​U​D |
| volgnummer | Uniek volgnummer van het ZAAK-INFORMATIEOBJECTTYPE binnen het ZAAKTYPE. | integer | ja | C​R​U​D |
| richting | Aanduiding van de richting van informatieobjecten van het gerelateerde INFORMATIEOBJECTTYPE bij zaken van het gerelateerde ZAAKTYPE.

Uitleg bij mogelijke waarden:

* `inkomend` - Inkomend
* `intern` - Intern
* `uitgaand` - Uitgaand | string | ja | C​R​U​D |
| statustype | URL-referentie naar het STATUSTYPE waarbij deze INFORMATIEOBJECTTYPEn verplicht aanwezig moeten zijn. | string | nee | C​R​U​D |

## ZaakTypenRelatie

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/zaaktypenrelatie)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| zaaktype | URL referentie naar het gerelateerde zaaktype, mogelijks in een extern ZTC. | string | ja | C​R​U​D |
| aardRelatie | Omschrijving van de aard van de relatie van zaken van het ZAAKTYPE tot zaken van het andere ZAAKTYPE

Uitleg bij mogelijke waarden:

* `vervolg` - Vervolg
* `bijdrage` - Bijdrage
* `onderwerp` - Onderwerp | string | ja | C​R​U​D |
| toelichting | Een toelichting op de aard van de relatie tussen beide ZAAKTYPEN. | string | nee | C​R​U​D |

## ZaakType

Objecttype op [GEMMA Online](https://www.gemmaonline.nl/index.php/Rgbz_1.0/doc/objecttype/zaaktype)

| Attribuut | Omschrijving | Type | Verplicht | CRUD* |
| --- | --- | --- | --- | --- |
| url | URL-referentie naar dit object. Dit is de unieke identificatie en locatie van dit object. | string | nee | ~~C~~​R​~~U~~​~~D~~ |
| identificatie | Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt. | string | nee | C​R​U​D |
| omschrijving | Omschrijving van de aard van ZAAKen van het ZAAKTYPE. | string | ja | C​R​U​D |
| omschrijvingGeneriek | Algemeen gehanteerde omschrijving van de aard van ZAAKen van het ZAAKTYPE | string | nee | C​R​U​D |
| vertrouwelijkheidaanduiding | Aanduiding van de mate waarin zaakdossiers van ZAAKen van dit ZAAKTYPE voor de openbaarheid bestemd zijn. Indien de zaak bij het aanmaken geen vertrouwelijkheidaanduiding krijgt, dan wordt deze waarde gezet.

Uitleg bij mogelijke waarden:

* `openbaar` - Openbaar
* `beperkt_openbaar` - Beperkt openbaar
* `intern` - Intern
* `zaakvertrouwelijk` - Zaakvertrouwelijk
* `vertrouwelijk` - Vertrouwelijk
* `confidentieel` - Confidentieel
* `geheim` - Geheim
* `zeer_geheim` - Zeer geheim | string | ja | C​R​U​D |
| doel | Een omschrijving van hetgeen beoogd is te bereiken met een zaak van dit zaaktype. | string | ja | C​R​U​D |
| aanleiding | Een omschrijving van de gebeurtenis die leidt tot het starten van een ZAAK van dit ZAAKTYPE. | string | ja | C​R​U​D |
| toelichting | Een eventuele toelichting op dit zaaktype, zoals een beschrijving van het procesverloop op de hoofdlijnen. | string | nee | C​R​U​D |
| indicatieInternOfExtern | Een aanduiding waarmee onderscheid wordt gemaakt tussen ZAAKTYPEn die Intern respectievelijk Extern geïnitieerd worden. Indien van beide sprake kan zijn, dan prevaleert de externe initiatie.

Uitleg bij mogelijke waarden:

* `inkomend` - Inkomend
* `intern` - Intern
* `uitgaand` - Uitgaand | string | ja | C​R​U​D |
| handelingInitiator | Werkwoord dat hoort bij de handeling die de initiator verricht bij dit zaaktype. Meestal &#39;aanvragen&#39;, &#39;indienen&#39; of &#39;melden&#39;. Zie ook het IOB model op https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.handeling_initiator | string | ja | C​R​U​D |
| onderwerp | Het onderwerp van ZAAKen van dit ZAAKTYPE. In veel gevallen nauw gerelateerd aan de product- of dienstnaam uit de Producten- en Dienstencatalogus (PDC). Bijvoorbeeld: &#39;Evenementenvergunning&#39;, &#39;Geboorte&#39;, &#39;Klacht&#39;. Zie ook het IOB model op https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.onderwerp | string | ja | C​R​U​D |
| handelingBehandelaar | Werkwoord dat hoort bij de handeling die de behandelaar verricht bij het afdoen van ZAAKen van dit ZAAKTYPE. Meestal &#39;behandelen&#39;, &#39;uitvoeren&#39;, &#39;vaststellen&#39; of &#39;onderhouden&#39;. Zie ook het IOB model op https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.handeling_behandelaar | string | ja | C​R​U​D |
| doorlooptijd | De periode waarbinnen volgens wet- en regelgeving een ZAAK van het ZAAKTYPE afgerond dient te zijn, in kalenderdagen. | string | ja | C​R​U​D |
| servicenorm | De periode waarbinnen verwacht wordt dat een ZAAK van het ZAAKTYPE afgerond wordt conform de geldende servicenormen van de zaakbehandelende organisatie(s). | string | nee | C​R​U​D |
| opschortingEnAanhoudingMogelijk | Aanduiding die aangeeft of ZAAKen van dit mogelijk ZAAKTYPE kunnen worden opgeschort en/of aangehouden. | boolean | ja | C​R​U​D |
| verlengingMogelijk | Aanduiding die aangeeft of de Doorlooptijd behandeling van ZAAKen van dit ZAAKTYPE kan worden verlengd. | boolean | ja | C​R​U​D |
| verlengingstermijn | De termijn (typisch een aantal dagen) waarmee de Doorlooptijd behandeling van ZAAKen van dit ZAAKTYPE kan worden verlengd. Mag alleen een waarde bevatten als verlenging mogelijk is. | string | nee | C​R​U​D |
| trefwoorden | Een trefwoord waarmee ZAAKen van het ZAAKTYPE kunnen worden gekarakteriseerd. | array | nee | C​R​U​D |
| publicatieIndicatie | Aanduiding of (het starten van) een ZAAK dit ZAAKTYPE gepubliceerd moet worden. | boolean | ja | C​R​U​D |
| publicatietekst | De generieke tekst van de publicatie van ZAAKen van dit ZAAKTYPE. | string | nee | C​R​U​D |
| verantwoordingsrelatie | De relatie tussen ZAAKen van dit ZAAKTYPE en de beleidsmatige en/of financiële verantwoording. | array | nee | C​R​U​D |
| productenOfDiensten | Het product of de dienst die door ZAAKen van dit ZAAKTYPE wordt voortgebracht. | array | ja | C​R​U​D |
| selectielijstProcestype | URL-referentie naar een vanuit archiveringsoptiek onderkende groep processen met dezelfde kenmerken (PROCESTYPE in de Selectielijst API). | string | nee | C​R​U​D |
| catalogus | URL-referentie naar de CATALOGUS waartoe dit ZAAKTYPE behoort. | string | ja | C​R​U​D |
| statustypen | URL-referenties naar de STATUSTYPEN die mogelijk zijn binnen dit ZAAKTYPE. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| resultaattypen | URL-referenties naar de RESULTAATTYPEN die mogelijk zijn binnen dit ZAAKTYPE. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| eigenschappen | URL-referenties naar de EIGENSCHAPPEN die aanwezig moeten zijn in ZAKEN van dit ZAAKTYPE. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| informatieobjecttypen | URL-referenties naar de INFORMATIEOBJECTTYPEN die mogelijk zijn binnen dit ZAAKTYPE. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| roltypen | URL-referenties naar de ROLTYPEN die mogelijk zijn binnen dit ZAAKTYPE. | array | nee | ~~C~~​R​~~U~~​~~D~~ |
| besluittypen | URL-referenties naar de BESLUITTYPEN die mogelijk zijn binnen dit ZAAKTYPE. | array | ja | C​R​U​D |
| deelzaaktypen | De ZAAKTYPE(n) waaronder ZAAKen als deelzaak kunnen voorkomen bij ZAAKen van dit ZAAKTYPE. | array | nee | C​R​U​D |
| gerelateerdeZaaktypen | De ZAAKTYPEn van zaken die relevant zijn voor zaken van dit ZAAKTYPE. | array | ja | C​R​U​D |
| beginGeldigheid | De datum waarop het is ontstaan. | string | ja | C​R​U​D |
| eindeGeldigheid | De datum waarop het is opgeheven. | string | nee | C​R​U​D |
| versiedatum | De datum waarop de (gewijzigde) kenmerken van het ZAAKTYPE geldig zijn geworden | string | ja | C​R​U​D |
| concept | Geeft aan of het object een concept betreft. Concepten zijn niet-definitieve versies en zouden niet gebruikt moeten worden buiten deze API. | boolean | nee | ~~C~~​R​~~U~~​~~D~~ |


* Create, Read, Update, Delete
