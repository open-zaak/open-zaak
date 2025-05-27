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

Naast de selectielijstklasse moet ook een afleidingswijze worden gekozen. De volgende combinaties van een selectielijst klasse en een afleidingswijze kunnen alleen met elkaar worden geselecteerd:

.. list-table::
    :header-rows: 1

    *   - Procestermijn
        - Afleidingswijze
    *   - nihil
        - afgehandeld
    *   - ingeschatte_bestaansduur_procesobject
        - termijn

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
    *   - Gerelateerde zaak
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
