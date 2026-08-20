.. _performance_index:

Performance
===========

Configuration
-------------

Each minor Open Zaak version should be deployed on the dedicated instance on Kubernetes for the performance testing.
The performance testing should be run both for at least ``GET /zaken/api/v1/zaken`` endpoint with
following configurations:

1. Locust users
    * 1 user
    * 16 users
2. Role
    * super user
    * regular user

For runs with 16 users Open Zaak should be deployed with enough amount of threads,
for example 4 processes and 4 threads.

Each run should last at least 5 minutes.

Hardware
--------

The following resources are used:

* Number of replicas: 10
* CPU per pod: 1000m (1 CPU)
* Memory per pod: 1Gi

Open Zaak data
--------------

There should be enough data in the database for the performance testing:

* 1.000.000 Zaken in the Zaken API
* 1.000.000 Documenten in the Documenten API
* 1.000.000 Besluiten in the Besluiten API
* 1 Catalogus with 100 Zaaktypen in the Catalogi API

Performance test results
------------------------

1 user
^^^^^^

====================== ========= ======================
OZ version             Role      Relative change to median time compared to previous version
====================== ========= ======================
1.20.0 (fuzzy on)      Superuser —
1.20.0 (fuzzy on)      Regular   —
1.21.0 (fuzzy on)      Superuser -68.75%
1.21.0 (fuzzy on)      Regular   -66.10%
1.21.1 (fuzzy on)      Superuser +6.67%
1.21.1 (fuzzy on)      Regular   +5.00%
1.21.2 (fuzzy on)      Superuser +0.00%
1.21.2 (fuzzy on)      Regular   +0.00%
1.22.0 (fuzzy on)      Superuser +6.25%
1.22.0 (fuzzy on)      Regular   +9.52%
1.23.0 (fuzzy on)      Superuser +0.00%
1.23.0 (fuzzy on)      Regular   +0.00%
1.24.0 (fuzzy on)      Superuser -11.76%
1.24.0 (fuzzy on)      Regular   +0.00%
1.25.0 (fuzzy on)      Superuser +6.67%
1.25.0 (fuzzy on)      Regular   +4.35%
1.26.0 (fuzzy on)      Superuser -12.50%
1.26.0 (fuzzy on)      Regular   -16.67%
1.27.0 (fuzzy on)      Superuser -14.29%
1.27.0 (fuzzy on)      Regular   -15.00%
1.28.0 (fuzzy on)      Superuser +8.33%
1.28.0 (fuzzy on)      Regular   +0.00%
1.29.0 (fuzzy on)      Superuser +0.00%
1.29.0 (fuzzy on)      Regular   +5.88%
1.30.0 (fuzzy on)      Superuser -11.76% (response time: 150ms)
1.30.0 (fuzzy on)      Regular   -9.09% (response time: 200ms)
====================== ========= ======================

16 users
^^^^^^^^

====================== ========= ======================
OZ version             Role      Relative change to median time (compared to previous version)
====================== ========= ======================
1.20.0 (fuzzy on)      Superuser —
1.20.0 (fuzzy on)      Regular   —
1.21.0 (fuzzy on)      Superuser -66.67%
1.21.0 (fuzzy on)      Regular   -67.01%
1.21.1 (fuzzy on)      Superuser +8.33%
1.21.1 (fuzzy on)      Regular   +6.25%
1.21.2 (fuzzy on)      Superuser 0.00%
1.21.2 (fuzzy on)      Regular   0.00%
1.22.0 (fuzzy on)      Superuser +11.54%
1.22.0 (fuzzy on)      Regular   +8.82%
1.23.0 (fuzzy on)      Superuser -3.45%
1.23.0 (fuzzy on)      Regular   0.00%
1.24.0 (fuzzy on)      Superuser +10.71%
1.24.0 (fuzzy on)      Regular   0.00%
1.25.0 (fuzzy on)      Superuser -3.23%
1.25.0 (fuzzy on)      Regular   +5.41%
1.26.0 (fuzzy on)      Superuser -20.00%
1.26.0 (fuzzy on)      Regular   -20.51%
1.27.0 (fuzzy on)      Superuser -8.33%
1.27.0 (fuzzy on)      Regular   -6.45%
1.28.0 (fuzzy on)      Superuser +4.55%
1.28.0 (fuzzy on)      Regular   +6.90%
1.29.0 (fuzzy on)      Superuser 0.00%
1.29.0 (fuzzy on)      Regular   +3.23%
1.30.0 (fuzzy on)      Superuser -0.00% (response time: 430ms)
1.30.0 (fuzzy on)      Regular   -0.00% (response time: 320ms)
====================== ========= ======================

Historical results for instance running in Docker
-------------------------------------------------

.. warning::

    The test results from 1.22.0 seem to have slightly degraded compared to 1.21.2,
    but this is only the case if the Open Zaak instance and Postgres database server are
    running on the same server. In most setups (like when using Kubernetes), this is not the case
    (see also https://github.com/psycopg/psycopg/issues/448)

1 user
^^^^^^

====================== ========= ======================
OZ version             Role      Median time (in ms, average over all endpoints)
====================== ========= ======================
1.9.0                  Superuser 740
1.9.0                  Regular   2500
1.10.2                 Superuser 790
1.10.2                 Regular   1600
1.13.0                 Superuser 860
1.13.0                 Regular   1700
1.14.0 (fuzzy on)      Superuser 640
1.14.0 (fuzzy on)      Regular   690
1.17.0 (fuzzy on)      Superuser 480
1.17.0 (fuzzy on)      Regular   610
1.18.0 (fuzzy on)      Superuser 510
1.18.0 (fuzzy on)      Regular   550
1.19.0 (fuzzy on)      Superuser 540
1.19.0 (fuzzy on)      Regular   610
1.20.0 (fuzzy on)      Superuser 570
1.20.0 (fuzzy on)      Regular   580
1.21.0 (fuzzy on)      Superuser 160
1.21.0 (fuzzy on)      Regular   220
1.21.1 (fuzzy on)      Superuser 150
1.21.1 (fuzzy on)      Regular   220
1.21.2 (fuzzy on)      Superuser 160
1.21.2 (fuzzy on)      Regular   200
1.22.0 (fuzzy on)      Superuser 160
1.22.0 (fuzzy on)      Regular   200
1.23.0 (fuzzy on)      Superuser 150
1.23.0 (fuzzy on)      Regular   190
====================== ========= ======================

16 users
^^^^^^^^

====================== ========= ======================
OZ version             Role      Median time (in ms, average over all endpoints)
====================== ========= ======================
1.9.0                  Superuser 2300
1.9.0                  Regular   13000
1.10.2                 Superuser 3200
1.10.2                 Regular   11000
1.13.0                 Superuser 3400
1.13.0                 Regular   11000
1.14.0 (fuzzy on)      Superuser 2600
1.14.0 (fuzzy on)      Regular   3400
1.17.0 (fuzzy on)      Superuser 3300
1.17.0 (fuzzy on)      Regular   4000
1.18.0 (fuzzy on)      Superuser 1900
1.18.0 (fuzzy on)      Regular   2300
1.19.0 (fuzzy on)      Superuser 2100
1.19.0 (fuzzy on)      Regular   2200
1.20.0 (fuzzy on)      Superuser 2200
1.20.0 (fuzzy on)      Regular   2100
1.21.0 (fuzzy on)      Superuser 390
1.21.0 (fuzzy on)      Regular   510
1.21.1 (fuzzy on)      Superuser 390
1.21.1 (fuzzy on)      Regular   510
1.21.1 (fuzzy on)      Superuser 400
1.21.1 (fuzzy on)      Regular   540
1.22.0 (fuzzy on)      Superuser 520
1.22.0 (fuzzy on)      Regular   660
1.23.0 (fuzzy on)      Superuser 500
1.23.0 (fuzzy on)      Regular   670
====================== ========= ======================


.. toctree::
   :maxdepth: 1
   :caption: Further reading

   profiling
   apachebench
   notifications
