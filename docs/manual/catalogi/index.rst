.. _manual_catalogi_index:

==================
Catalogusbeheer
==================

.. note:: Om catalogussen te kunnen beheren moet je tot de **Catalogi admin**
   groep behoren of equivalente permissies hebben. Zie
   :ref:`manual_users_groups` voor groepenbeheer.

Catalogus aanmaken
==================

Om aan de gang te kunnen met catalogusbeheer moet er eerst een catalogus aangemaakt worden,
dit kan door via de beginpagina van de admin te klikken op **Catalogi** onder het kopje **Gegevens**
en vervolgens op de knop **Catalogus toevoegen** rechtsbovenin te klikken.

.. image:: assets/create_catalogus.png
    :width: 100%
    :alt: Catalogus toevoegen

Op de volgende pagina dienen minimaal alle dikgedrukte velden ingevuld te worden,
waarna er op de **OPSLAAN** knop rechtsonderin de pagina geklikt kan worden.

Zaaktype aanmaken
=================

Na het toevoegen van de catalogus kan er een Zaaktype toegevoegd worden aan deze
catalogus door te klikken op **Toon Zaaktypen** onder het kopje **ACTIES**.

.. image:: assets/toon_zaaktypen.png
    :width: 100%
    :alt: Toon alle zaaktypen

Vervolgens dient er geklikt te worden op de **Zaaktype toevoegen** knop rechtsbovenin.
Op de volgende pagina is het aan te maken zaaktype al gekoppeld aan de juiste catalogus
en moet alleen de overige verplichte informatie nog ingevuld worden. Als alle verplichte
velden gevuld zijn, kan het zaaktype opgeslagen worden door te klikken op de knop
**Opslaan en opnieuw bewerken**, onderaan de pagina

.. image:: assets/zaaktype_opslaan.png
    :width: 100%
    :alt: Zaaktype publiceren

Zaaktype publiceren
===================

Het zojuist aangemaakt zaaktype is nog een concept, wat inhoudt dat dit zaaktype
niet gebruikt kan worden buiten de Catalogi API zelf (er kunnen bijvoorbeeld nog
geen Zaken aangemaakt worden met dit zaaktype). Om ervoor te zorgen dat dit wel mogelijk is,
moet het zaaktype eerst gepubliceerd worden. Dit kan door te klikken op de **Publiceren**
knop, onderaan de detail pagina van het zaaktype.

.. image:: assets/zaaktype_publiceren.png
    :width: 100%
    :alt: Zaaktype opslaan en opnieuw bewerken

**LET OP**: als er op de detailpagina van het zaaktype aanpassingen gemaakt worden en
er vervolgens op **Publiceren** gedrukt wordt, dan worden deze aanpassingen opgeslagen.

Een nieuwe versie van een zaaktype aanmaken
===========================================

Om een nieuwe versie van een zaaktype toe te voegen, moet eerst de datum einde
geldigheid van het zaaktype ingevuld worden.

.. image:: assets/set_eind_geldigheid.png
    :width: 100%
    :alt: Zet datum einde geldigheid van zaaktypen

Zodra dit gedaan is, kan er door te klikken op de **Nieuwe versie toevoegen**
knop een nieuwe versie van het zaaktype aangemaakt worden

.. image:: assets/nieuwe_versie.png
    :width: 100%
    :alt: Nieuwe versie van zaaktype toevoegen

Als er genavigeerd wordt naar de zaaktypen van de aangemaakte catalogus, is de
nieuwe versie te zien. De nieuwe versie zal eerst gepubliceerd moeten worden voor gebruik
buiten de Catalogi API.

.. image:: assets/all_zaaktypen.png
    :width: 100%
    :alt: Lijst met alle zaaktypen van catalogus

Exporteren/importeren van een catalogus
=======================================

Een catalogus kan samen met alle typen die erin zitten (Zaaktypen, Informatieobjecttype, etc.)
geëxporteerd worden naar een .zip archief, dat vervolgens weer gebruikt kan worden om
de catalogus in een andere Catalogi API te importeren.

Om dit te doen in OpenZaak, dient er op de te exporteren catalogus geklikt te worden
onder **Gegevens** > **Catalogi** en kan er vervolgens op de **Exporteren** knop
onderaan de pagina geklikt worden. Daarna kan de export gedownload worden als .zip-bestand.

.. image:: assets/catalogus_export.png
    :width: 100%
    :alt: Exporteren van een catalogus

Om de importfunctionaliteit te demonstreren is de zojuist geëxporteerde
catalogus verwijderd uit de OpenZaak admin. Dit kan gedaan worden door de catalogus
bij de lijstweergave van Catalogi aan te vinken, de actie **Geselecteerde catalogi verwijderen**
te kiezen en op uitvoeren te drukken.

.. image:: assets/delete_catalogus.png
    :width: 100%
    :alt: Verwijderen van een catalogus

De catalogus kan nu geïmporteerd worden door op dezelfde pagina te klikken
op de **Importeer catalogus** knop rechtsbovenin. Op de volgende pagina moet
het .zip-bestand geupload worden en kan er aangegeven worden
of er voor de objecten nieuwe UUIDs gegenereerd moeten worden, of dat de bestaande
UUIDs uit de import gebruikt kunnen worden.

.. image:: assets/import_catalogus.png
    :width: 100%
    :alt: Importeren van een catalogus

**LET OP**: alle Zaaktypen, Informatieobjecttypen en Besluittypen worden geïmporteerd
als concept.

Exporteren/importeren van een zaaktype
======================================

In sommige gevallen hoeft niet een gehele catalogus geïmporteerd te worden,
maar alleen een enkel zaaktype uit die catalogus, dit is ook mogelijk in de OpenZaak admin.

Om te demonstreren hoe het importeren werkt als er Informatieobjecttypen en Besluittypen
gerelateerd zijn aan het Zaaktype, worden deze voor deze tutorial eerst toegevoegd aan het zaaktype.
Dit kan door te navigeren naar de catalogi lijstweergave, te klikken op **Toon alle besluittypen**,
daarna te klikken op **Besluittype toevoegen**, de benodigde informatie in te vullen en
het te exporteren zaaktype selecteren (hetzelfde geldt voor Informatieobjecttypen).

Zodra dit gedaan is, kan het zaaktype geëxporteerd door te klikken op **Export**
onderaan de pagina van het zaaktype en zal er weer een .zip-bestand aangeboden worden.
Om hierna het importeren te demonstreren, wordt dit zaaktype verwijderd door te klikken op
**Verwijderen** linksonderin de zaaktype pagina.

.. image:: assets/export_zaaktype.png
    :width: 100%
    :alt: Exporteren van een zaaktype

Vervolgens kan de catalogus, waarin het zaaktype terecht moet komen,
aangeklikt worden en kan onderaan de cataloguspagina de knop **Import ZaakType**
aangeklikt worden.

.. image:: assets/import_zaaktype.png
    :width: 100%
    :alt: Importeren van een zaaktype

Op de volgende pagina wordt de export van het zaaktype geupload.

.. image:: assets/import_zaaktype_file.png
    :width: 100%
    :alt: Zaaktype export uploaden

Omdat er in de .zip ook Besluittypen en Informatieobjecttypen zitten, moet er bepaald
worden of deze ook geïmporteerd moeten worden, of dat deze vervangen kunnen worden door
bestaande Besluittypen en Informatieobjecttypen. Aangezien het Besluittype en Informatieobjecttype
in deze tutorial niet zijn verwijderd, wordt er hier voor gekozen om de bestaande typen
te gebruiken. Vervolgens kan er op **Select** geklikt worden en zal de import uitgevoerd worden.

.. image:: assets/import_zaaktype_file.png
    :width: 100%
    :alt: Zaaktype export uploaden
