## Notificaties
## Berichtkenmerken voor Open Zaak API

Kanalen worden typisch per component gedefinieerd. Producers versturen berichten op bepaalde kanalen,
consumers ontvangen deze. Consumers abonneren zich via een notificatiecomponent (zoals <a href="https://notificaties-api.vng.cloud/api/v1/schema/" rel="nofollow">https://notificaties-api.vng.cloud/api/v1/schema/</a>) op berichten.

Hieronder staan de kanalen beschreven die door deze component gebruikt worden, met de kenmerken bij elk bericht.

De architectuur van de notificaties staat beschreven op <a href="https://github.com/VNG-Realisatie/notificaties-api" rel="nofollow">https://github.com/VNG-Realisatie/notificaties-api</a>.


### autorisaties

**Kanaal**
`autorisaties`

**Main resource**

`applicatie`



**Kenmerken**



**Resources en acties**


* <code>applicatie</code>: create, update, destroy


### besluiten

**Kanaal**
`besluiten`

**Main resource**

`besluit`



**Kenmerken**

* `verantwoordelijke_organisatie`: Het RSIN van de niet-natuurlijk persoon zijnde de organisatie die het besluit heeft vastgesteld.
* `besluittype`: URL-referentie naar het BESLUITTYPE (in de Catalogi API).
* `besluittype.catalogus`: **EXPERIMENTEEL** URL-referentie naar de CATALOGUS waartoe dit BESLUITTYPE behoort.

**Resources en acties**


* <code>besluit</code>: create, update, destroy

* <code>besluitinformatieobject</code>: create, destroy


### besluittypen

**Kanaal**
`besluittypen`

**Main resource**

`besluittype`



**Kenmerken**

* `catalogus`: URL-referentie naar de CATALOGUS waartoe dit BESLUITTYPE behoort.

**Resources en acties**


* <code>besluittype</code>: create, update, destroy


### documenten

**Kanaal**
`documenten`

**Main resource**

`enkelvoudiginformatieobject`



**Kenmerken**

* `bronorganisatie`: Het RSIN van de Niet-natuurlijk persoon zijnde de organisatie die het informatieobject heeft gecreëerd of heeft ontvangen en als eerste in een samenwerkingsketen heeft vastgelegd.
* `informatieobjecttype`: URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API).
* `vertrouwelijkheidaanduiding`: Aanduiding van de mate waarin het INFORMATIEOBJECT voor de openbaarheid bestemd is.
* `informatieobjecttype.catalogus`: **EXPERIMENTEEL** URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort.

**Resources en acties**


* <code>enkelvoudiginformatieobject</code>: create, update, destroy

* <code>gebruiksrechten</code>: create, update, destroy

* <code>verzending</code>: create, update, destroy


### informatieobjecttypen

**Kanaal**
`informatieobjecttypen`

**Main resource**

`informatieobjecttype`



**Kenmerken**

* `catalogus`: URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort.

**Resources en acties**


* <code>informatieobjecttype</code>: create, update, destroy


### zaaktypen

**Kanaal**
`zaaktypen`

**Main resource**

`zaaktype`



**Kenmerken**

* `catalogus`: URL-referentie naar de CATALOGUS waartoe dit ZAAKTYPE behoort.

**Resources en acties**


* <code>zaaktype</code>: create, update, destroy


### zaken

**Kanaal**
`zaken`

**Main resource**

`zaak`



**Kenmerken**

* `bronorganisatie`: Het RSIN van de Niet-natuurlijk persoon zijnde de organisatie die de zaak heeft gecreeerd. Dit moet een geldig RSIN zijn van 9 nummers en voldoen aan <a href="https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef" rel="nofollow">https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef</a>
* `zaaktype`: URL-referentie naar het ZAAKTYPE (in de Catalogi API).
* `zaaktype.catalogus`: **EXPERIMENTEEL** URL-referentie naar de CATALOGUS waartoe dit ZAAKTYPE behoort.
* `vertrouwelijkheidaanduiding`: Aanduiding van de mate waarin het zaakdossier van de ZAAK voor de openbaarheid bestemd is.

**Resources en acties**


* <code>zaak</code>: create, update, destroy

* <code>status</code>: create

* <code>zaakobject</code>: create, update, destroy

* <code>zaakinformatieobject</code>: create

* <code>zaakeigenschap</code>: create, update, destroy

* <code>klantcontact</code>: create

* <code>rol</code>: create, update, destroy

* <code>resultaat</code>: create, update, destroy

* <code>zaakbesluit</code>: create

* <code>zaakcontactmoment</code>: create

* <code>zaakverzoek</code>: create


