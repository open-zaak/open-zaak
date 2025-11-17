.. _installation_observability_logging:

=======
Logging
=======

Logging is the practice of emitting log messages that describe what is happening in the
system, or "events" in short. Log events can have varying degrees of severity, such as
``debug``, ``info``, ``warning``, ``error`` or even ``critical``. By default, Open Zaak
emits logs with level ``info`` and higher.

A collection of log events with a correlation ID (like a request or trace ID) allow one
to reconstruct the chain of events that took place which lead to a particular outcome.

Open Zaak emits structured logs in JSON format (unless explicitly configured otherwise),
which should make log aggregation and analysis easier.

We try to keep a consistent log message structure, where the following keys
are (usually) present:

``source``
    The component in the application stack that produced the log entry. Typical
    values are ``uwsgi`` and ``app``.

``level``
    The severity level of the log message. One of ``debug``, ``info``, ``warning``,
    ``error`` or ``critical``.

``timestamp``
    The moment when the log entry was produced, a string in ISO-8601 format. Most of
    the logs have microsecond precision, but some of them are limited to second
    precision.

``event``
    The event that occurred, e.g. ``request_started`` or ``spawned worker (PID 123)``.
    This gives the semantic meaning to the log entry.

Other keys that frequently occur are:

``request_id``
    Present for application logs emitted during an HTTP request, makes it possible to
    correlate multiple log entries for a single request. Not available in logs emitted
    by background tasks or logs emitted before/after the Open Zaak app.

.. tip:: Certain log aggregation solutions require you to configure "labels" to extract
   for efficient querying. You can use the above summary of log context keys to configure
   this according to your needs.

.. note:: We can not 100% guarantee that every log message will always be JSON due to
   limitations in third party software/packages that we use. Most (if not all) log
   aggregation technologies support handling both structured and unstructured logs.


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

* ``deprecated_endpoint_called``: a deprecated endpoint was called. Additional context: ``endpoint``.

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

Convenience endpoints
^^^^^^^^^^^^^^^^^^^^^

* ``zaak_geregistreerd`` (INFO). Additional context: ``zaak_url``, ``status_url``, ``rollen_urls``, ``zaakinformatieobjecten_urls``, ``zaakobjecten_urls``.
* ``zaak_opgeschort`` (INFO). Additional context: ``zaak_url``, ``status_url``.
* ``zaak_verlengd`` (INFO). Additional context: ``zaak_url``, ``status_url``.
* ``zaak_bijgewerkt`` (INFO). Additional context: ``zaak_url``, ``status_url``, ``rollen_urls``.
* ``zaak_afgesloten`` (INFO). Additional context: ``zaak_url``, ``status_url``, ``resultaat_url``.
* ``besluit_verwerkt`` (INFO). Additional context: ``besluit_url``. ``besluitinformatieobjecten_urls``.
* ``document_geregistreerd`` (INFO). Additional context: ``enkelvoudiginformatieobject_url``. ``zaak_url``.

.. _manual_logging_exceptions:

Exceptions
----------

Handled exceptions follow a standardized JSON format to ensure consistency and improve error tracking.
Most fields are standard and include:
``title``, ``code``, ``status``, ``event``, ``source``, ``user_id``, ``request_id``, ``exception_id``, ``timestamp``, ``logger`` and ``level``.

A new field ``invalid_params`` has been added to provide detailed information about which input parameters caused the error in API calls.

    - ``name``: name of the invalid parameter
    - ``code``: specific error code
    - ``reason``: explanation/message of the error

.. code-block:: json

    {
        "title": "'Je hebt geen toestemming om deze actie uit te voeren.'",
        "code": "invalid-client-identifier",
        "status": 403,
        "invalid_params": [
            {
                "name": "",
                "code": "invalid-client-identifier",
                "reason": "Client identifier bestaat niet"
            }
        ],
        "event": "api.handled_exception",
        "exception_id": "96af71a2-5b1d-40db-b177-f595cbf0f847",
        "source": "app",
        "timestamp": "2025-10-03T09:55:43.796277Z",
        "logger": "vng_api_common.exception_handling",
        "level": "error"
    }

Uncaught exceptions that occur via the API are logged as ``api.uncaught_exception`` events
and contain the traceback of the exception.

.. code-block:: json

    {
        "message": "division by zero",
        "event": "api.uncaught_exception",
        "source": "app",
        "timestamp": "2025-09-30T14:40:06.276604Z",
        "logger": "vng_api_common.views",
        "level": "error",
        "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/rest_framework/views.py\", line 497, in dispatch\n    self.initial(request, *args, **kwargs)\n  File \"/usr/local/lib/python3.12/site-packages/vng_api_common/geo.py\", line 30, in initial\n    super().initial(request, *args, **kwargs)\n  File \"/usr/local/lib/python3.12/site-packages/rest_framework/views.py\", line 415, in initial\n    self.check_permissions(request)\n  File \"/usr/local/lib/python3.12/site-packages/rest_framework/views.py\", line 332, in check_permissions\n    if not permission.has_permission(request, self):\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/src/openzaak/utils/decorators.py\", line 53, in convert_exceptions\n    response = function(*args, **kwargs)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/src/openzaak/utils/permissions.py\", line 122, in has_permission\n    1 / 0\n    ~^~~\nZeroDivisionError: division by zero"
    }

Third party library events
--------------------------

For more information about log events emitted by third party libraries, refer to the documentation
for that particular library

* :ref:`Django (via django-structlog) <request_events>`
* :ref:`Celery (via django-structlog) <request_events>`
