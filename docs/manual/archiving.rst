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
       | hoofdzaak, ingangsdatum_besluit, vervaldatum_besluit,
       | zaakobject
   * - ingeschatte_bestaansduur_procesobject
     - | termijn
   * - vast_te_leggen_datum
     - | ander_datumkenmerk, eigenschap, gerelateerde_zaak (deprecated),
       | hoofdzaak, ingangsdatum_besluit, vervaldatum_besluit,
       | zaakobject
   * - samengevoegd_met_bewaartermijn
     - | ander_datumkenmerk, eigenschap, gerelateerde_zaak (deprecated),
       | hoofdzaak, ingangsdatum_besluit, vervaldatum_besluit,
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
