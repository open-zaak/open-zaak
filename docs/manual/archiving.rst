.. _archiving:

===========
Archivering
===========


Resultaattype
=============

Selectielijstklasse
-------------------

Tijdens het aanmaken van een resultaattype, moet een selectielijstklasse worden geselecteerd. Een selectielijstklasse heeft een van de volgende procestermijnen:

.. list-table::
   :widths: 20
   :header-rows: 1

   * - Procestermijnen
   * - nihil
   * - bestaansduur_procesobject
   * - ingeschatte_bestaansduur_procesobject
   * - vast_te_leggen_datum
   * - samengevoegd_met_bewaartermijn

Afleidingswijze
---------------

Naast de selectielijstklasse moet ook een afleidingswijze worden gekozen. In de volgende tabel is te zien welke afleidingswijzen zijn toegestaan per procestermijn.
``nihil`` + ``afgehandeld`` & ``ingeschatte_bestaansduur_procesobject`` + ``termijn`` kunnen alleen in combinatie met elkaar worden geselecteerd.
De andere afleidingswijzen zijn toegestaan bij de andere procestermijnen

.. list-table::
   :header-rows: 1

   * - procestermijn
     - toegestane afleidingswijzen
   * - nihil
     - afgehandeld
   * - bestaansduur_processobject
     - | ander_datumkenmerk, eigenschap, gerelateerde_zaak (deprecated),
       | hoofdzaak, ingangsdatum_besluit, termijn, vervaldatum_besluit,
       | zaakobject
   * - ingeschatte_bestaansduur_procesobject
     - | termijn
   * - vast_te_leggen_datum
     - | ander_datumkenmerk, eigenschap, gerelateerde_zaak (deprecated),
       | hoofdzaak, ingangsdatum_besluit, termijn, vervaldatum_besluit,
       | zaakobject
   * - samengevoegd_met_bewaartermijn
     - | ander_datumkenmerk, eigenschap, gerelateerde_zaak (deprecated),
       | hoofdzaak, ingangsdatum_besluit, termijn, vervaldatum_besluit,
       | zaakobject

Daarnaast zijn bij de bepaling van de brondatum archiefprocedure per afleidingswijze een aantal velden verplicht:

.. list-table::
    :header-rows: 1

    *   - Afleidingswijze
        - Procestermijn
        - Datumkenmerk
        - Einddatum bekend
        - Objecttype
        - Registratie
    *   - afgehandeld
        -
        -
        -
        -
        -
    *   - Ander datumkenmerk
        -
        - X
        -
        - X
        - X
    *   - Eigenschap
        -
        - X
        -
        -
        -
    *   - Gerelateerde zaak (deprecated)
        -
        -
        -
        -
        -
    *   - Hoofdzaak
        -
        -
        -
        -
        -
    *   - Ingangsdatum besluit
        -
        -
        -
        -
        -
    *   - Termijn
        - X
        -
        -
        -
        -
    *   - Vervaldatum besluit
        -
        -
        -
        -
        -
    *   - Zaakobject
        -
        - X
        -
        - X
        -

Bepaling van de archiefparameters
---------------------------------

Bij het sluiten van een zaak worden twee datums gezet die van belang zijn voor archivering:

* ``startdatum_bewaartermijn``: soms ook de brondatum genoemd.
* ``archiefactiedatum``: uitkomst van ``startdatum_bewaartermijn`` + ``archiefactietermijn`` van het resultaattype.

Hieronder is per afleidingswijze beschreven welke waarde gebruikt wordt voor ``startdatum_bewaartermijn``.

* ``afgehandeld``: ``Zaak.einddatum``.
* ``ander_datumkenmerk``: ``startdatum_bewaartermijn`` dient handmatig gezet te worden.
* ``eigenschap``: de ``waarde`` van de ZaakEigenschap waarvan de ``naam`` overeenkomt met het ``datumkenmerk`` van het resultaattype.
* ``hoofdzaak``: de ``einddatum`` van de hoofdzaak.
* ``ingangsdatum_besluit``: de ``ingangsdatum`` van het gekoppelde Besluit.
* ``vervaldatum_besluit``: de ``vervaldatum`` van het gekoppelde Besluit. Doordat dit attribuut
  niet verplicht is, kan het zijn dat deze op het moment van sluiten van de zaak nog leeg is.
  Zodra de ``vervaldatum`` gezet wordt, worden de archiefparameters ook gezet.
* ``termijn``: ``Zaak.einddatum`` + ``ResultaatType.procestermijn``.
* ``zaakobject``: op basis van ``ResultaatType.objecttype`` wordt het gerelateerde ``ZaakObject``
  geselecteerd, en de waarde het attribuut dat zich bevind op het pad gespecificeerd in ``ResultaatType.datumkenmerk``
  wordt gebruikt als ``startdatum_bewaartermijn``.

Bij alle bovenstaande afleidingswijzen (behalve ``ander_datumkenmerk`` en ``termijn``)
worden de archiefparameters herberekend als de attributen waarop deze datums gebaseerd zijn
aangepast worden. Bovendien zorgt het verwijderen van een resultaat van een zaak ervoor
dat deze datums op ``null`` gezet worden.
