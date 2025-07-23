.. _api_experimental:


=======================================
Experimental features of Open Zaak APIs
=======================================

Open Zaak implements APIs, which adhere to :ref:`VNG standards <api_index>`.
Moreover it provides extra features which are not included in the standards.
All such features are marked as "experimental" (or "experimenteel") in the OAS.

There are no breaking changes from the VNG standards and these changes are mostly small
additions for the convenience of the clients. Below is the full list of deviations.

Zaken API
=========

Notities
-------------

The ``zaaknotities`` endpoint has been added to the Zaken API and supports GET, POST, PUT, PATCH and DELETE operations.

* ``/api/v1/zaaknotities``

Notifications
-------------

For ``zaken`` notification channel a new "kenmerk" ``zaaktype.catalogus`` is added.

Endpoints
---------

New endpoints are added:

* PUT ``/api/v1/rollen/{uuid}``
* POST ``/api/v1/zaaknummer_reserveren`` – reserve a zaaknummer (identificatie) in combination with a bronorganisatie.
  The optional ``amount`` attribute can be specified to reserve identifications in bulk
* ``/api/v1/zaak_registreren`` – create a zaak in combination with a status, rollen, zaakinformatieobjecten & zaakobjecten to immediately link it to a zaak.
* GET ``/api/v1/substatussen``
* POST ``/api/v1/substatussen``

Attributes
----------

* ``ZaakEigenschap``:

    * ``waarde`` attribute is changed: an extra validation is added against
      ``eigenschap.specificatie`` value if ``ZAAK_EIGENSCHAP_WAARDE_VALIDATION``
      env variable is turned on

* Request body of ``/api/v1/zaken/_zoek``:
    * ``zaaktype__not_in`` search attribute is added

* ``Rol``:
    * ``betrokkeneIdentificatie.identificatie`` max length is changed from 24 to 128  for ``betrokkeneType: "medewerker"``
    * ``betrokkeneIdentificatie.nietNatuurlijkPersoonIdentificatie.kvkNummer`` is added to
      support :ref:`mandates <client-development-mandate>`
    * ``betrokkeneIdentificatie.vestigingsNummer`` is added for ``betrokkeneType: "niet_natuurlijk_persoon"``
        as ``betrokkeneType: "vestiging"`` has been deprecated.
    * ``roltoelichting`` is changed to not required
    * Two attributes are added to track the validity period of a ``Rol`` within a ``Zaak``:

            * ``beginGeldigheid``: the date on which the validity period starts
            * ``eindeGeldigheid``: the date on which the validity period ends

* ``Zaak``:
    * ``communicatiekanaalNaam`` is added
    * ``relevanteAndereZaken.aardRelatie`` is changed: a new enum value "overig" is added
    * ``relevanteAndereZaken.overigeRelatie`` is added
    * ``relevanteAndereZaken.toelichting`` is added
    * ``opschorting.eerdereOpschorting`` is added to indicate whether or not a `Zaak` has been suspended in the past

Query parameters
----------------

* ``/api/v1/rollen`` endpoint. Added new parameters to support :ref:`mandates <client-development-mandate>`:
    * ``betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer``
    * ``betrokkeneIdentificatie__nietNatuurlijkPersoon__vestigingsNummer``
    * ``betrokkeneIdentificatie__vestiging__kvkNummer`` **(scheduled for deprecation in Open Zaak version 3.0)**
    * ``machtiging``
    * ``machtiging__loa``

* ``/api/v1/zaken`` endpoint. Added new parameters to support :ref:`mandates <client-development-mandate>`:
    * ``rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer``
    * ``rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__vestigingsNummer``
    * ``rol__betrokkeneIdentificatie__vestiging__kvkNummer`` **(scheduled for deprecation in Open Zaak version 3.0)**
    * ``rol__machtiging``
    * ``rol__machtiging__loa``

* ``/api/v1/zaken`` endpoint. Other new parameters:
    * ``kenmerk__bron``
    * ``kenmerk`` A bron-kenmerk combination of a zaak. (format: ``<bron>:<kenmerk>``)
    * ``status__statustype`` – filter Zaken by the current status that has the given statustype. Accepts a statustype URL.
    * ``resultaat__resultaattype`` – filter Zaken by the resultaat with the specified resultaattype. Accepts a resultaattype URL.

Documenten API
==============

Notifications
-------------

For ``documenten`` notification channel a new "kenmerk" ``informatieobjecttype.catalogus`` is added.

Endpoints
---------

New import endpoints are added:

* ``/import/create``
* ``/import/{uuid}/upload``
* ``/import/{uuid}/status``
* ``/import/{uuid}/report``
* ``/import/{uuid}/delete``

The usage of import endpoints is described :ref:`here <installation_reference_import>`.

New endpoints are added:

* ``/api/v1/documentnummer_reserveren`` – reserve a documentnummer (identificatie) in combination with a bronorganisatie.
  The optional ``amount`` attribute can be specified to reserve identifications in bulk
* ``/api/v1/document_registreren`` – create a enkelvoudiginformatieobject in combination with a zaakinformatieobject to immediately link it to a zaak.

Query parameters
----------------

* ``/api/v1/enkelvoudiginformatieobjecten`` endpoint. Added new parameters:

    * ``auteur``
    * ``beschrijving``
    * ``creatiedatum__gte``
    * ``creatiedatum__lte``
    * ``informatieobjecttype``
    * ``locked``
    * ``objectinformatieobjecten__object``
    * ``objectinformatieobjecten__objectType``
    * ``ordering``
    * ``titel``
    * ``trefwoorden__overlap``
    * ``vertrouwelijkheidaanduiding``


Catalogi API
============

Attributes
----------

* ``ResultaatType``:

    * ``brondatumArchiefprocedure.datumkenmerk`` is changed and supports nested path as value

* ``StatusType``:
    * ``eigenschappen`` is made read-only. `The reason <https://github.com/VNG-Realisatie/gemma-zaken/issues/2343>`__

* ``BesluitType``, ``Eigenschap``, ``InformatieObjectType``, ``ZaakType``, ``ResultaatType``,
  ``RolType``, ``StatusType``, ``ZaakObjectType``:

    * ``beginObject`` and ``eindeObject`` are made read-only. `The reason <https://github.com/VNG-Realisatie/gemma-zaken/issues/2332>`__

Query parameters
----------------

* ``/api/v1/informatieobjecttypen`` endpoint. Added new parameters:
    * ``zaaktype``

* ``/api/v1/roltypen`` endpoint. Added new parameters:
    * ``omschrijving`` - filter by (a part of the) ``omschrijving`` (case-insensitive match).

Besluiten API
=============

Notifications
-------------

For ``besluiten`` notification channel a new "kenmerk" ``besluittype.catalogus`` is added.

Endpoints
---------

New endpoints are added:

* ``/api/v1/besluit_verwerken`` – create a besluit in combination with one or more besluitinformatieobject(en) to immediately link them.


Autorisaties API
================

No deviation from the standard
