.. _manual_logging:

Logging
=======

Format
------

Open Zaak emits structured logs (using `structlog <https://www.structlog.org/en/stable/>`_).
A log line can be formatted like this:

.. code-block:: json

    {
        "uuid": "20d23f12-6743-486c-a1f2-c31c5c6a86f9",
        "identificatie": "ABC-1",
        "vertrouwelijkheidaanduiding": "openbaar",
        "event": "zaak_created",
        "user_id": null,
        "request_id": "2f9e9a5b-d549-4faa-a411-594aa8a52eee",
        "timestamp": "2025-05-19T14:09:20.339166Z",
        "logger": "openzaak.components.zaken.api.viewsets",
        "level": "info"
    }

Each log line will contain an ``event`` type, a ``timestamp`` and a ``level``.
Dependent on your configured ``LOG_LEVEL`` (see :ref:`installation_env_config` for more information),
only log lines with of that level or higher will be emitted.

Open Zaak log events
--------------------

Below is the list of logging ``event`` types that Open Zaak can emit. In addition to the mentioned
context variables, these events will also have the **request bound metadata** described in the :ref:`django-structlog documentation <request_events>`.

API
~~~
* ``applicatie_created``: created an ``Applicatie`` via the API. Additional context: ``uuid``, ``client_id``.
* ``applicatie_deleted``: deleted an ``Applicatie`` via the API. Additional context: ``uuid``, ``client_id``.
* ``applicatie_updated``: updated an ``Applicatie`` via the API. Additional context: ``uuid``, ``client_id``, ``partial``.


* ``bestandsdeel_uploaded``: uploaded a ``Bestandsdeel`` via the API. Additional context: ``uuid``, ``client_id``.

* ``besluit_created``: created a ``Besluit`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluit_delete_failed``: failed to delete a ``Besluit`` via the API. Additional context: ``uuid``, ``client_id``, ``error``.
* ``delete_remote_zaakbesluit_failed``: failed to delete the remote ``ZaakBesluit`` relation. Additional context: ``uuid``, ``client_id``, ``error``, ``zaakbesluit_url``.
* ``besluit_deleted``: deleted a ``Besluit`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluit_updated``: updated a ``Besluit`` via the API. Additional context: ``uuid``, ``client_id``,``partial``.

* ``besluitinformatieobject_created``: created a ``BesluitInformatieObject`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluitinformatieobject_delete_failed``: failed to delete a ``BesluitInformatieObject`` via the API. Additional context: ``uuid``, ``client_id``, ``error``.
* ``delete_remote_oio_failed``: failed to delete the remote ``ObjectInformatieObject`` relation. Additional context: ``uuid``, ``client_id``, ``error``, ``objectinformatieobject_url``.
* ``besluitinformatieobject_deleted``: deleted a ``BesluitInformatieObject`` via the API. Additional context: ``uuid``, ``client_id``.

* ``besluittype_created``: created a ``Besluittype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluittype_delete_failed``: failed to delete a remote ``Besluittype``. Additional context: ``uuid``, ``client_id``, ``error``.
* ``besluittype_deleted``: deleted a ``Besluittype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluittype_published``: published a ``Besluittype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``besluittype_updated``: updated a ``Besluittype`` via the API. Additional context: ``uuid``, ``client_id``.

* ``catalogus_created``: created a ``Catalogus`` via the API. Additional context: ``uuid``, ``client_id``.

* ``delete_remote_oio_failed``: failed to delete a remote objectinformatieobject. Additional context: ``uuid``, ``client_id``, ``objectinformatieobject_url``, ``error``.
* ``delete_remote_zaakbesluit_failed``: failed to delete a remote zaakbesluit. Additional context: ``uuid``, ``client_id``, ``zaakbesluit_url``, ``error``.

* ``enkelvoudiginformatieobject_created``: created an ``EnkelvoudigInformatieObject`` via the API. Additional context: ``uuid``, ``client_id``.
* ``enkelvoudiginformatieobject_updated``: updated an ``EnkelvoudigInformatieObject`` via the API. Additional context: ``uuid``, ``client_id``.

* ``eigenschap_created``: created an ``Eigenschap`` via the API. Additional context: ``uuid``, ``client_id``.
* ``eigenschap_delete_failed``: failed to delete a remote ``Eigenschap``. Additional context: ``uuid``, ``client_id``, ``error``.
* ``eigenschap_deleted``: deleted an ``Eigenschap`` via the API. Additional context: ``uuid``, ``client_id``.
* ``eigenschap_updated``: updated an ``Eigenschap`` via the API. Additional context: ``uuid``, ``client_id``.

* ``gebruiksrechten_created``: created a ``Gebruiksrechten`` via the API. Additional context: ``uuid``, ``client_id``.
* ``gebruiksrechten_deleted``: deleted a ``Gebruiksrechten`` via the API. Additional context: ``uuid``, ``client_id``.
* ``gebruiksrechten_updated``: updated a ``Gebruiksrechten`` via the API. Additional context: ``uuid``, ``client_id``, ``partial``.

* ``informatieobjecttype_created``: created an InformatieObjectType via the API. Additional context: ``uuid``, ``client_id``.
* ``informatieobjecttype_delete_failed``: failed to delete an InformatieObjectType via the API. Additional context: ``uuid``, ``client_id``, ``error``.
* ``informatieobjecttype_deleted``: deleted an InformatieObjectType via the API. Additional context: ``uuid``, ``client_id``.
* ``informatieobjecttype_published``: published an InformatieObjectType via the API. Additional context: ``uuid``, ``client_id``.
* ``informatieobjecttype_updated``: updated an InformatieObjectType via the API. Additional context: ``uuid``, ``client_id``.

* ``klantcontact_created``: created a Klantcontact via the API. Additional context: uuid, zaak_uuid, client_id.

* ``objectinformatieobject_created``: created an ``ObjectInformatieObject`` via the API. Additional context: ``informatieobject``, ``object``, ``object_type``, ``client_id``.
* ``objectinformatieobject_deleted``: deleted an ``ObjectInformatieObject`` via the API. Additional context: ``uuid``, ``object``, ``client_id``.

* ``reserved_document_created``: created a single ``ReservedDocument`` via the API. Additional context: ``identificatie``, ``bronorganisatie``, ``aantal``, ``client_id``.
* ``reserved_document_created_bulk``: created multiple ``ReservedDocuments`` via the API. Additional context: ``identificaties``, ``bronorganisatie``, ``aantal``, ``client_id``.

* ``resultaat_created``: created a Resultaat via the API. Additional context: ``uuid``, ``zaak_uuid``, ``resultaattype``, ``client_id``.
* ``resultaat_deleted``: deleted a Resultaat via the API. Additional context: ``uuid``, ``zaak_uuid``, ``resultaattype``, ``client_id``.
* ``resultaat_updated``: updated a Resultaat via the API. Additional context: ``uuid``, ``zaak_uuid``, ``resultaattype``, ``client_id``.

* ``resultaattype_created``: created a ``Resultaattype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``resultaattype_deleted``: deleted a ``Resultaattype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``resultaattype_updated``: updated a ``Resultaattype`` via the API. Additional context: ``uuid``, ``client_id``.

* ``rol_created``: created a Rol via the API. Additional context: ``uuid``, ``zaak_uuid``, ``betrokkene_type``, ``betrokkene_identificatie``, ``client_id``.
* ``rol_deleted``: deleted a Rol via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``rol_updated``: updated a Rol via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.

* ``roltype_created``: created a ``Roltype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``roltype_deleted``: deleted a ``Roltype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``roltype_updated``: updated a ``Roltype`` via the API. Additional context: ``uuid``, ``client_id``.

* ``statustype_created``: created a ``Statustype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``statustype_deleted``: deleted a ``Statustype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``statustype_updated``: updated a ``Statustype`` via the API. Additional context: ``uuid``, ``client_id``.

* ``status_created``: created a ``Status`` via the API. Additional context: ``uuid``, ``zaak_uuid``, ``statustype``, ``gezetdoor``.

* ``verzending_created``: created a ``Verzending`` via the API. Additional context: ``data``, ``status_code``, ``client_id``.
* ``verzending_deleted``: deleted a ``Verzending`` via the API. Additional context: ``uuid``, ``status_code``, ``client_id``.
* ``verzending_updated``: updated a ``Verzending`` via the API. Additional context: ``uuid``, ``data``, ``status_code``, ``client_id``.

* ``zaak_created``: created a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.
* ``zaak_deleted``: deleted a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.
* ``zaak_updated``: updated a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.

* ``zaakbesluit_created_external``: created a relation to an external Besluit via the API. Additional context: ``besluit_uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_deleted_external``: deleted a relation to an external Besluit via the API. Additional context: ``besluit_uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_relation_deleted``: deleted a relation to a local Besluit via the API. Additional context: ``besluit_uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_relation_exists``: relation to a Besluit already exists. Additional context: ``besluit_uuid``, ``zaak_uuid``, ``client_id``.

* ``zaakeigenschap_created``: created a ZaakEigenschap via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.

* ``zaakinformatieobject_created``: created a ZaakInformatieObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakinformatieobject_deleted``: deleted a ZaakInformatieObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``informatieobject_url``, ``client_id``.
* ``zaakinformatieobject_updated``: updated a ZaakInformatieObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.

* ``zaaknummer_gereserveerd``: reserved one or more Zaak identifications via the API. Additional context: ``client_id``, ``path``, ``method``, ``input_data``, ``response_data``, ``count``.

* ``zaakobject_created``: created a ZaakObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``object_url``, ``object_type``, ``client_id``.
* ``zaakobject_deleted``: deleted a ZaakObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakobject_updated``: updated a ZaakObject via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.

* ``zaakobjecttype_created``: created a ``ZaakObjectType`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaakobjecttype_deleted``: deleted a ``ZaakObjectType`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaakobjecttype_updated``: updated a ``ZaakObjectType`` via the API. Additional context: ``uuid``, ``client_id``.

* ``zaaktype_created``: created a ``Zaaktype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_deleted``: deleted a ``Zaaktype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_published``: published a ``Zaaktype`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_updated``: updated a ``Zaaktype`` via the API. Additional context: ``uuid``, ``client_id``.

* ``zaaktype_informatieobjecttype_created``: created a ``ZaakTypeInformatieObjectType`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_informatieobjecttype_updated``: updated a ``ZaakTypeInformatieObjectType`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_informatieobjecttype_deleted``: deleted a ``ZaakTypeInformatieObjectType`` via the API. Additional context: ``uuid``, ``client_id``.
* ``zaaktype_informatieobjecttype_delete_blocked``: blocked deletion of a ``ZaakTypeInformatieObjectType`` due to a non-concept relation. Additional context: ``uuid``, ``client_id``, ``reason``.

* ``zaakverzoek_created``: created a ZaakVerzoek via the API. Additional context: ``client_id``, ``status_code``, ``path``, ``method``, ``data``, ``uuid``.
* ``zaakverzoek_deleted``: deleted a ZaakVerzoek via the API. Additional context: ``client_id``, ``status_code``.

* ``zaakcontactmoment_created``: created a ZaakContactmoment via the API. Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``status_code``.
* ``zaakcontactmoment_deleted``: deleted a ZaakContactmoment via the API. Additional context: ``client_id``, ``status_code``.

Third party library events
--------------------------

For more information about log events emitted by third party libraries, refer to the documentation
for that particular library

* :ref:`Django (via django-structlog) <request_events>`
* :ref:`Celery (via django-structlog) <request_events>`
