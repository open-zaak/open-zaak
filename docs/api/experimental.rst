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

Notifications
-------------

For ``zaken`` notification channel a new "kenmerk" ``zaaktype.catalogus`` is added.

Endpoints
---------

New endpoints are added:

* PUT ``/api/v1/rollen/{uuid}``
* POST ``/api/v1/reserveer_zaaknummer``

Attributes
----------

* ``ZaakEigenschap``:

    * ``waarde`` attribute is changed: an extra validation is added against
      ``eigenschap.specificatie`` value if ``ZAAK_EIGENSCHAP_WAARDE_VALIDATION``
      env variable is turned on

* Request body of ``/api/v1/zaken/_zoek``:
    * ``zaaktype__not_in`` search attribute is added

* ``Rol``:
    * ``betrokkeneIdentificatie.nietNatuurlijkPersoonIdentificatie.kvkNummer`` is added to
      support :ref:`mandates <client-development-mandate>`
    * ``roltoelichting`` is changed to not required
    * Two attributes are added to track the validity period of a ``Rol`` within a ``Zaak``:

            * ``beginGeldigheid``: the date on which the validity period starts
            * ``eindeGeldigheid``: the date on which the validity period ends

* ``Zaak``:
    * ``communicatiekanaalNaam`` is added
    * ``relevanteAndereZaken.aardRelatie`` is changed: a new enum value "overig" is added
    * ``relevanteAndereZaken.overigeRelatie`` is added
    * ``relevanteAndereZaken.toelichting`` is added

Query parameters
----------------

* ``/api/v1/rollen`` endpoint. Added new parameters to support :ref:`mandates <client-development-mandate>`:
    * ``betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer``
    * ``betrokkeneIdentificatie__vestiging__kvkNummer``
    * ``machtiging``
    * ``machtiging__loa``

* ``/api/v1/zaken`` endpoint. Added new parameters to support :ref:`mandates <client-development-mandate>`:
    * ``rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer``
    * ``rol__betrokkeneIdentificatie__vestiging__kvkNummer``
    * ``rol__machtiging``
    * ``rol__machtiging__loa``


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


Besluiten API
=============

Notifications
-------------

For ``besluiten`` notification channel a new "kenmerk" ``besluittype.catalogus`` is added.


Autorisaties API
================

No deviation from the standard
