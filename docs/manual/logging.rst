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

The events below are emitted when API operations are performed.

* ``applicatie_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``applicatie_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``applicatie_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``besluit_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluit_delete_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``.
* ``besluit_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluit_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``besluitinformatieobject_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluitinformatieobject_delete_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``.
* ``besluitinformatieobject_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluittype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluittype_delete_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``.
* ``besluittype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluittype_published`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``besluittype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``bestandsdeel_uploaded`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``catalogus_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``delete_remote_oio_failed`` (ERROR) failed to delete the remote ``ObjectInformatieObject`` relation. Additional context: ``client_id``, ``uuid``, ``error``, ``objectinformatieobject_url``.
* ``delete_remote_zaakbesluit_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``, ``zaakbesluit_url``.
* ``eigenschap_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``eigenschap_delete_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``.
* ``eigenschap_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``eigenschap_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``enkelvoudiginformatieobject_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``enkelvoudiginformatieobject_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``gebruiksrechten_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``gebruiksrechten_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``gebruiksrechten_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``informatieobjecttype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``informatieobjecttype_delete_failed`` (ERROR). Additional context: ``client_id``, ``uuid``, ``error``.
* ``informatieobjecttype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``informatieobjecttype_published`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``informatieobjecttype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``klantcontact_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``objectinformatieobject_created`` (INFO). Additional context: ``client_id``, ``informatieobject``, ``object``, ``object_type``.
* ``objectinformatieobject_deleted`` (INFO). Additional context: ``client_id``, ``uuid``, ``object``.
* ``reserved_document_created_bulk`` (INFO). Additional context: ``client_id``, ``bronorganisatie``, ``aantal``, ``identificaties``.
* ``reserved_document_created`` (INFO). Additional context: ``client_id``, ``bronorganisatie``, ``identificatie``, ``aantal``.
* ``document_geregistreerd`` (INFO). Additional context: ``enkelvoudiginformatieobject_url``. ``zaak_url``.
* ``resultaat_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``resultaat_deleted`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``resultaat_updated`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.
* ``resultaattype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``resultaattype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``resultaattype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``rol_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``rol_deleted`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``rol_updated`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.
* ``roltype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``roltype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``roltype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``status_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``statustype``, ``gezetdoor``.
* ``statustype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``statustype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``statustype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``verzending_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``verzending_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``verzending_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``zaak_created`` (INFO). Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``, ``zaaktype``.
* ``zaak_deleted`` (INFO). Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``, ``zaaktype``.
* ``zaak_updated`` (INFO). Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``, ``zaaktype``, ``partial``.
* ``zaakbesluit_created_external`` (INFO). Additional context: ``besluit_url``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_deleted_external`` (INFO). Additional context: ``uuid``, ``besluit_url``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_relation_deleted`` (INFO). Additional context: ``uuid``, ``besluit_url``, ``zaak_uuid``, ``client_id``.
* ``zaakbesluit_relation_exists`` (INFO) relation to a Besluit already exists. Additional context: ``besluit_url``, ``zaak_uuid``, ``client_id``.
* ``zaakcontactmoment_created`` (INFO). Additional context: ``client_id``, ``uuid``, ``zaak_uuid``.
* ``zaakcontactmoment_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaakeigenschap_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakeigenschap_deleted`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakeigenschap_updated`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.
* ``zaakinformatieobject_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakinformatieobject_deleted`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakinformatieobject_updated`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.
* ``zaaknummer_gereserveerd`` (INFO) reserved one or more Zaak identifications. Additional context: ``client_id``, ``path``, ``method``, ``input_data``, ``response_data``, ``count``.
* ``zaakobject_created`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``object_url``, ``object_type``, ``client_id``.
* ``zaakobject_deleted`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``.
* ``zaakobject_updated`` (INFO). Additional context: ``uuid``, ``zaak_uuid``, ``client_id``, ``partial``.
* ``zaakobjecttype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaakobjecttype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaakobjecttype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``zaaktype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaaktype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaaktype_informatieobjecttype_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaaktype_informatieobjecttype_delete_blocked`` (WARNING) blocked deletion of a ``ZaakTypeInformatieObjectType`` due to a non-concept relation. Additional context: ``client_id``, ``uuid``, ``reason``.
* ``zaaktype_informatieobjecttype_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaaktype_informatieobjecttype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``zaaktype_published`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaaktype_updated`` (INFO). Additional context: ``client_id``, ``uuid``, ``partial``.
* ``zaakverzoek_created`` (INFO). Additional context: ``client_id``, ``uuid``.
* ``zaakverzoek_deleted`` (INFO). Additional context: ``client_id``, ``uuid``.

Third party library events
--------------------------

For more information about log events emitted by third party libraries, refer to the documentation
for that particular library

* :ref:`Django (via django-structlog) <request_events>`
* :ref:`Celery (via django-structlog) <request_events>`
