.. _performance_index:

Performance
===========

Configuration
-------------

Each minor Open Zaak version should be deployed on the dedicated server for the performance testing.
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

The dedicated service where all the tests are run has the following configuration:

* Processor: 4 CPUs at 3.2 GHz
* RAM: 16 GB
* Storage: 4 TB SATA

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

================= ========= ======================
OZ version        Role      Median time (in ms)
================= ========= ======================
1.9.0             Superuser 740
1.9.0             Regular   2500
1.10.2            Superuser 790
1.10.2            Regular   1600
1.13.0            Superuser 860
1.13.0            Regular   1700
1.14.0 (fuzzy on) Superuser 640
1.14.0 (fuzzy on) Regular   690
1.17.0 (fuzzy on) Superuser 480
1.17.0 (fuzzy on) Regular   610
1.18.0 (fuzzy on) Superuser 510
1.18.0 (fuzzy on) Regular   550
1.19.0 (fuzzy on) Superuser 540
1.19.0 (fuzzy on) Regular   610
================= ========= ======================

16 users
^^^^^^^^

================= ========= ======================
OZ version        Role      Median time (in ms)
================= ========= ======================
1.9.0             Superuser 2300
1.9.0             Regular   13000
1.10.2            Superuser 3200
1.10.2            Regular   11000
1.13.0            Superuser 3400
1.13.0            Regular   11000
1.14.0 (fuzzy on) Superuser 2600
1.14.0 (fuzzy on) Regular   3400
1.17.0 (fuzzy on) Superuser 3300
1.17.0 (fuzzy on) Regular   4000
1.18.0 (fuzzy on) Superuser 1900
1.18.0 (fuzzy on) Regular   2300
1.19.0 (fuzzy on) Superuser 2100
1.19.0 (fuzzy on) Regular   2200
================= ========= ======================


.. toctree::
   :maxdepth: 1
   :caption: Further reading

   profiling
   apachebench
   notifications
