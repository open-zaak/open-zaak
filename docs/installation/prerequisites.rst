.. _installation_prerequisites:

Prerequisites
=============

Open Zaak is most often deployed as a Docker container. While the
`container images <https://hub.docker.com/r/openzaak/open-zaak/>`_ contain all the
necessary dependencies, Open Zaak does require extra service to deploy the full stack.
These dependencies and their supported versions are documented here.

The ``docker-compose.yml`` (not suitable for production usage!) in the root of the
repository also describes these dependencies.

PostgreSQL with Postgis
-----------------------

Open Zaak currently only supports PostgreSQL as datastore. The Zaken API are geo-capable,
which requires the postgis_ extension to be enabled.

The supported versions in the table below are tested in the CI pipeline. Other versions
*may* work but we offer no guarantees.

============ ============ ============ ============ ============ ============
Matrix       Postgres 10  Postgres 11  Postgres 12  Postgres 13  Postgres 14
============ ============ ============ ============ ============ ============
Postgis 2.5  V            V            V            X            X
Postgis 3.2  V            V            V            V            V
============ ============ ============ ============ ============ ============

.. warning:: Open Zaak only supports maintained versions of PostgreSQL. Once a version is
   `EOL <https://www.postgresql.org/support/versioning/>`_, support will
   be dropped in the next release.

.. _postgis: https://postgis.net/

Redis
-----

Open Zaak uses Redis as a cache backend, especially relevant for admin sessions, and a task
queue broker.

Supported versions: 5, 6

Reverse proxy (nGINX)
---------------------

The Open Zaak Documents API serves uploaded files after verifying the permissions. The
actual file-serving is delegated to the reverse proxy through the ``X-Sendfile``
feature. By default, Open Zaak is configured for nGINX and will emit the ``X-Accel``
header.

You can use alternative reverse proxy implementations and configure this through the
``SENDFILE_BACKEND`` environment variable. See the
`django-sendfile2 <https://django-sendfile2.readthedocs.io/en/latest/backends.html>`_
documentation for available backends.


.. note:: If you are not using the Open Zaak Documents API, but an alternative
   implementation, then this requirement becomes obsolete.


Background tasks
----------------

Open Zaak uses `Celery`_ an asynchronous task queue to send notifications. If sending
notifications is turned on, the task workers should be run. Each worker can be run in
a separate container.

The ``docker-compose.yml`` in the root of the repository includes the example of Celery
worker container.

.. _Celery: https://docs.celeryq.dev/en/stable/