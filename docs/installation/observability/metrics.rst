.. _installation_observability_metrics:

=======
Metrics
=======

Open Zaak produces application metrics (using Open Telemetry).

.. note:: The exact metric names that show up may be transformed, e.g. Prometheus replaces
   periods with underscores, and processing pipelines may add prefixes or suffixes.

.. important:: Some metrics are defined as "global scope".

   These metrics are typically derived from application state introspection, e.g. by
   performing database (read) queries to aggregate some information. Usually those
   correspond to an `Asynchronous Gauge <https://opentelemetry.io/docs/specs/otel/metrics/api/#asynchronous-gauge>`_.

   Multiple replicas and/or instances of the same service will produce the same values
   of the metrics. You need to apply some kind of aggregation to de-duplicate these
   values. The attribute ``scope="global"``  acts as a marker for these type of metrics.

   With PromQL for example, you can use ``avg`` on the assumption that all values will
   be equal, so the average will also be identical:

   .. code-block:: promql

       avg by (type) (otel_openzaak_auth_user_count{scope="global"})

Generic
=======

``http.server.duration``
    Captures how long each HTTP request took, in ms. The metric produces histogram data.

``http.server.request.duration`` (not active)
    The future replacement of ``http.server.duration``, in seconds. Currently not
    enabled, but the code is in the Open Telemetry SDK instrumentation already and could
    possibly be opted-in to.

Application specific
====================

Accounts
--------

``openzaak.auth.user_count``
    Reports the number of users in the database. This is a global metric, you must take
    care in de-duplicating results. Additional attributes are:

    - ``scope`` - fixed, set to ``global`` to enable de-duplication.
    - ``type`` - the user type. ``all``, ``staff`` or ``superuser``.

    Sample PromQL query:

    .. code-block:: promql

        max by (type) (last_over_time(
          otel_openzaak_auth_user_count{scope="global"}
          [1m]
        ))

``openzaak.auth.login_failures``
    A counter incremented every time a user login fails (typically because of invalid
    credentials). Does not include the second factor, if enabled. Additional attributes:

    - ``http_target`` - the request path where the login failure occurred, if this
      happened in a request context.

``openzaak.auth.user_lockouts``
    A counter incremented every time a user is locked out because they reached the
    maximum number of failed attempts. Additional attributes:

    - ``http_target`` - the request path where the login failure occurred, if this
      happened in a request context.
    - ``username`` - username of the user trying to log in.

``openzaak.auth.logins``
    Counter incrementing on every successful login by a user. Additional attributes:

    - ``http_target`` - the request path where the login failure occurred, if this
      happened in a request context.
    - ``username`` - username of the user trying to log in.

``openzaak.auth.logouts``
    Counter incrementing every time a user logs out. Additional attributes:

    - ``username`` - username of the user who logged out.

Zaken
--------------


``openzaak.zaak.creates``
    Reports the number of zaken created via the API.

``openzaak.zaak.updates``
    Reports the number of zaken updated via the API.

``openzaak.zaak.deletes``
    Reports the number of zaken deleted via the API.

The zaken metrics show how many entities are created, updated, or deleted via the API,
helping to monitor load and the most frequent operations, and allow for various aggregations on the data.

    Sample PromQL query:

    .. code-block:: promql

        sum by (otel_scope_name) (otel_openzaak_zaak_updates_total)
