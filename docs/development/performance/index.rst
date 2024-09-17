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

Open Zaak data
--------------

There should be enough data in the database for the performance testing:

* 1.000.000 Zaken in the Zaken API
* 1.000.000 Documenten in the Documenten API
* 1.000.000 Besluiten in the Besluiten API
* 1 Catalogus with 100 Zaaktypen in the Catalogi API



.. toctree::
   :maxdepth: 1
   :caption: Further reading

   profiling
   apachebench
   notifications
