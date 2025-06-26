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

* ``zaak_created``: created a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.
* ``zaak_updated``: updated a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.
* ``zaak_deleted``: deleted a ``Zaak`` via the API. Additional context: ``uuid``, ``identificatie``, ``vertrouwelijkheidaanduiding``.


Third party library events
--------------------------

For more information about log events emitted by third party libraries, refer to the documentation
for that particular library

* :ref:`Django (via django-structlog) <request_events>`
* :ref:`Celery (via django-structlog) <request_events>`
