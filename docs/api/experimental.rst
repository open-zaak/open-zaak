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
--------

The ``zaaknotities`` endpoint has been added to the Zaken API and supports GET, POST, PUT, PATCH and DELETE operations.

* ``/api/v1/zaaknotities``

Notifications
-------------

For ``zaken`` notification channel a new "kenmerk" ``zaaktype.catalogus`` is added.

.. _cloud_events:

Cloud events
------------

Sending of cloud events is still under development and **NOT** suited for production use,
but currently Open Zaak can emit the following cloud events if configured:

* ``zaak-gemuteerd``: currently only emitted via POST on /statussen when creating a new Status for a Zaak
* ``zaak-verwijderd``: when deleting a Zaak
* ``zaak-geopend``: when the Zaak information is seen by the end user (can be triggered with a PATCH on only ``Zaak.laatstGeopend``)

A webhook endpoint ``/events`` has been added where incoming events can be delivered.

.. warning::

   In order to make sure that cloud events are only sent when the initial Zaak is "complete" (meaning that it has all the required resources to be considered a valid Zaak, such as a Rol for the `initiator`), the assumption is made that the initial Status will only be set by client applications once the initial Zaak is complete (meaning that the Rollen already exist before adding the Status). No validation exists for this currently, but in the future this will likely be enforced via validation on the API endpoints.

Example of a ``zaak-gemuteerd`` cloud event in its current shape:

.. code-block:: json

        {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak-gemuteerd",
            "source": "urn:nld:oin:01823288444:zakensysteem",
            "subject": "89b06186-c133-4c74-8492-b43392bc4fdb",
            "id": "b386ff52-de66-4fde-805f-6c80b4f3cc68",
            "time": "2025-11-28T09:57:45Z",
            "dataref": "/zaken/api/v1/zaken/89b06186-c133-4c74-8492-b43392bc4fdb",
            "datacontenttype": "application/json",
            "data": {}
        }

The shape of these cloud events and the actions that trigger these cloud events are still subject to change.
Currently these events are sent directly to a configured webhook, but in the future it will
be possible to route these cloud events via Open Notificaties as well.

Endpoints
---------

New endpoints are added:

* PUT ``/api/v1/rollen/{uuid}``
* POST ``/api/v1/zaaknummer_reserveren`` – reserve a zaaknummer (identificatie) in combination with a bronorganisatie.
  The optional ``amount`` attribute can be specified to reserve identifications in bulk
* POST ``/api/v1/zaak_registreren`` – create a zaak in combination with a status, rollen, zaakinformatieobjecten & zaakobjecten to immediately link them to this zaak.
* POST ``/api/v1/zaak_opschorten/{uuid}`` - suspend a zaak and set a new status for the zaak
* POST ``/api/v1/zaak_verlengen/{uuid}`` - extend a zaak and set a new status for the zaak
* POST ``/api/v1/zaak_bijwerken/{uuid}`` - update a zaak in combination with a status & rollen to immediately link them to this zaak.
* POST ``/api/v1/zaak_afsluiten/{uuid}`` - close a zaak by creating a status and resultaat for the zaak.
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
    * ``laatstGemuteerd`` is added to indicate when the latest Status change happened for the Zaak
    * ``laatstGeopend`` is added to indicate when the Zaak was last opened/seen by the end user (citizen)
    * ``betalingsindicatie`` has new enum values, the original values have been marked as deprecated

        * ``gefactureerd``: Invoice order sent
        * ``gecrediteerd``: Credit order sent
        * ``betaald``: Payment established (for example via online checkout with direct application)
        * ``nvt``: No costs involved

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
    * ``brondatumArchiefprocedure.afleidingswijze``: ``gerelateerde_zaak`` has been marked as deprecated

* ``StatusType``:
    * ``eigenschappen`` is made read-only. `The reason <https://github.com/VNG-Realisatie/gemma-zaken/issues/2343>`__

* ``BesluitType``, ``Eigenschap``, ``InformatieObjectType``, ``ZaakType``, ``ResultaatType``,
  ``RolType``, ``StatusType``, ``ZaakObjectType``:

    * ``beginObject`` and ``eindeObject`` are made read-only. `The reason <https://github.com/VNG-Realisatie/gemma-zaken/issues/2332>`__

Query parameters
----------------

* ``/api/v1/informatieobjecttypen`` endpoint. Added new parameters:
    * ``zaaktype``
    * ``omschrijving__icontains`` - filter by (a part of the) ``omschrijving`` (case-insensitive match).

* ``/api/v1/roltypen`` endpoint. Added new parameters:
    * ``omschrijving`` - filter by (a part of the) ``omschrijving`` (case-insensitive match).

* ``/api/v1/zaakobjecttypen`` endpoint. Added new parameters:
    * ``status`` – filter ZaakObjectType by concept status: "concept", "definitief", or "alles"

* ``/api/v1/zaaktypen`` endpoint. Added new parameters:
    * ``omschrijving__icontains`` – filter by (a part of the) ``zaaktype_omschrijving`` (case-insensitive match).
    * ``identificatie__icontains`` – filter by (a part of the) ``identificatie`` (case-insensitive match).

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
