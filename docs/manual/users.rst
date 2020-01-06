.. _manual_users:

=================
Gebruikerstoegang
=================

.. note:: Om gebruikers te kunnen beheren moet je tot de **User admin**
   groep behoren of equivalente permissies hebben. Zie
   :ref:`manual_users_groups` voor groepenbeheer.

.. _manual_users_groups:

Groepen
=======

Een *groep* is een set van permissies. Een permissie laat een gebruiker toe om
iets te doen. Typisch zijn er vier soorten permissies voor een soort van
gegeven:

* objecten lezen
* objecten aanmaken
* objecten aanpassen
* objecten verwijderen

Een gebruiker kan tot meerdere groepen behoren - de permissies vullen mekaar
dan aan, d.w.z. dat je de gecombineerde set van permissies krijgt van elke
groep.

Een standaard Open Zaak installatie komt met een aantal standaardgroepen:

**Admin**
    Een beheerder die alles kan. Ga hier erg zorgvuldig mee om!

**API admin**
    Leden van deze groep kunnen taakapplicaties en hun API-toegang instellen,
    en Open Zaak configureren om andere API's te consumeren.

**Autorisaties admin**
    Leden van deze groep kunnen taakapplicaties en hun API-toegang instellen,
    en Open Zaak configureren om andere API's te consumeren.

**Autorisaties lezen**
    Leden van deze groep kunnen zien welke applicaties toegang hebben tot de
    Open Zaak API's, maar deze niet bewerken.

**Besluiten admin**
    Leden van de groep kunnen de resources ontsloten via de *Besluiten API*
    lezen, aanmaken en bewerken:

    * Besluiten
    * Relaties tussen besluiten en documenten

**Besluiten lezen**
    Leden van de groep kunnen de resources ontsloten via de *Besluiten API*
    lezen.

**Catalogi admin**
    Leden van de groep kunnen de resources ontsloten via de *Catalogi API*
    lezen, aanmaken en bewerken:

    * Catalogi
    * Zaaktypen
    * Statustypen
    * Resultaattypen
    * Eigenschappen
    * Roltypen
    * Informatieobjecttypen
    * Besluittypen
    * Zaaktype-informatieobjecttypen

**Catalogi lezen**
    Leden van de groep kunnen de resources ontsloten via de *Catalogi API*
    lezen.

**Documenten admin**
    Leden van de groep kunnen de resources ontsloten via de *Documenten API*
    lezen, aanmaken en bewerken:

    * Enkelvoudige informatieobjecten (= documenten) met versiehistorie
    * Gebruiksrechten van documenten
    * Relaties tussen documenten en andere objecten

**Documenten lezen**
    Leden van de groep kunnen de resources ontsloten via de *Documenten API*
    lezen.

**Zaken admin**
    Leden van de groep kunnen de resources ontsloten via de *Zaken API*
    lezen, aanmaken en bewerken:

    * Zaken
    * Statussen van zaken
    * Resultaat van zaken
    * Eigenschappen van zaken
    * Documenten bij zaken
    * Andere objecten bij zaken
    * Klantcontacten van zaken
    * Betrokkenen bij zaken
    * Relevante zaak-relaties

**Zaken lezen**
    Leden van de groep kunnen de resources ontsloten via de *Zaken API*
    lezen.

.. _manual_users_add:

Een gebruiker aanmaken (en aan een groep toevoegen)
===================================================

.. _manual_users_group_add:

Een custom groep aanmaken
=========================

.. note:: Om groepen te kunnen beheren moet je tot de **Admin**
   groep behoren of equivalente permissies hebben. Zie
   :ref:`manual_users_groups` voor groepenbeheer.
