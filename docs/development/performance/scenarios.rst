.. _performance_scenarios:

=====================
Measuring performance
=====================

Goal
====

The purpose of performance measurements is to gain insight into the relationships
between system requirements, number of users and response times of the API's. From these
relationships we can draw up the minimum system requirements, depending on the number
of users, on which the API's still perform acceptable.

A standardized performance measurement also provides insight into which effect various
optimizations have.

Technical test scenarios
========================

The performance of some often used API-calls (requests) is measured to gain insights in
the technical performance.

**Zaken API**

1. Retrieve ZAAKen (``GET /api/v1/zaken``)
2. Retrieve ZAAK (``GET /api/v1/zaken/d4d..2e8``)
3. Create ZAAK (``POST /api/v1/zaken``)

**Catalogi API**

1. Retrieve ZAAKTYPEn (``GET /api/v1/zaaktypen``)
2. Retrieve ZAAKTYPE (``GET /api/v1/zaaktypen/d4d..2e8``)
3. Create ZAAKTYPE (``POST /api/v1/zaaktypen``)

**Besluiten API**

1. Retrieve BESLUITen (``GET /api/v1/besluit``)
2. Retrieve BESLUIT (``GET /api/v1/besluit/d4d..2e8``)
3. Create BESLUIT (``POST /api/v1/besluit``)

**Documenten API**

1. Retrieve ENKELVOUDIGINFORMATIEOBJECTen (``GET /api/v1/enkelvoudiginformatieobjecten``)
2. Retrieve ENKELVOUDIGINFORMATIEOBJECT (``GET /api/v1/enkelvoudiginformatieobjecten/d4d..2e8``)
3. Create ENKELVOUDIGINFORMATIEOBJECT (``POST /api/v1/enkelvoudiginformatieobjecten``)

Test specification
------------------

Using scenarios
~~~~~~~~~~~~~~~

A scenario in this test specification is equal to an API-call (request). Each API
resource is continuously without any delay, or *waiting time*, between each request.
This way, we can determine the maximum number of requests per second and average
response times.

Virtual users
~~~~~~~~~~~~~

We test with an increasing number of virtual users, from 1 to 100, that concurrently
execute the test scenarios. A virtual user is technically a script that executes the
different scenarios one after another. This way, we see the number of virtual users
that concurrently access the API's and its impact on performance.

Testdata
~~~~~~~~

The testset that is present in the database:

* 1.000.000 Zaken in the Zaken API
* 1.000.000 Documenten in the Documenten API
* 1.000.000 Besluiten in the Besluiten API
* 1 Catalogus with 100 Zaaktypen in the Catalogi API

Functional test scenarios
=========================

Performance testing is done by accessing the APIs as if they were being used by an
application, or a virtual system. Some typical functional scenarios have been observed
in similar systems:

1. Retrieve Zaken overview
2. Retrieve Zaken overview for a specific Zaaktype
3. Search Zaken by location
4. Search Zaken by person
5. Retrieve Zaak details
6. Retrieve history
7. Create Zaak
8. Add Status
9. Add Betrokkene
10. Add Document
11. Add Besluit
12. Add Resultaat

Scenario's in API-verzoeken
---------------------------

All functional scenarios have been translated into API requests. The number of API
requests, the exact query parameters for filtering and/or sorting lists, and the data
sent for creating objects are all very dynamic in practice. For each functional
scenario, one or more specific API requests are prepared that fill in the scenario as
well as possible.

A number of API requests have been placed out of scope because they are not part of
the *APIs voor Zaakgericht werken* but are most likely required to build a functional
user interface.

Retrieve Zaken overview (1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve an unfiltered list of Zaken, along with their Zaaktype and Statustype.

**Zaken API**

* 1x ZAAKen retrieve (``GET /api/v1/zaken``)
* 1x STATUSsen retrieve (``GET /api/v1/statussen``)

**Catalogi API**

* 1x ZAAKTYPEn retrieve (``GET /api/v1/zaaktypen``)
* 1x STATUSTYPEn retrieve (``GET /api/v1/statustypen``)

Retrieve Zaken overview for a specific Zaaktype (2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve an unfiltered list of Zaken, along with their Zaaktype and Statustype. Each
Status is requested, filtered on their matching Statustype for the appropriate Zaaktype.

**Zaken API**

* 1x ZAAKen retrieve (``GET /api/v1/zaken?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 3x STATUSsen retrieve (``GET /api/v1/statussen?statustype=/api/v1/statustypen/f82..396``)

**Catalogi API**

* 1x ZAAKTYPEn retrieve (``GET /api/v1/zaaktypen/011..3c1``)
* 1x STATUSTYPEn retrieve (``GET /api/v1/statustypen?zaaktype=/api/v1/zaaktypen/011..3c1``)

Search Zaken by location (3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a list of Zaken that match a specific geographical area (polygon).

**Zaken API**

* 1x ZAAKen zoeken (``POST /api/v1/zaken/_zoek``)

Search Zaken by person (4)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a list of Zaken that match a specific person (Betrokkene).

* *1x Betrokkene zoeken (buiten scope)*

**Zaken API**

* 1x ZAAKen filteren ``GET /api/v1/rollen?betrokkene=https://personen/api/v1/a66c38``

Retrieve Zaak details (5)
~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a complete Zaak, with its Resultaat, Besluit, 3 Documenten, *2 Zaakobjecten*
and *3 Betrokkenen*.

* *3x Betrokkenen retrieve via ROLlen-resultaat (buiten scope)*
* *2x Objecten retrieve via ZAAKOBJECTen-resultaat (buiten scope)*

**Zaken API**

* 1x ZAAK retrieve (``GET /api/v1/zaken/d4d..2e8``)
* 1x STATUSsen retrieve (``GET /api/v1/statussen?zaak=/api/v1/zaken/d4d..2e8``)
* 1x RESULTAAT retrieve (``GET /api/v1/resultaten/f84..e9e``)
* 1x ROLlen retrieve (``GET /api/v1/rollen?zaak=/api/v1/zaken/d4d..2e8``)
* 1x ZAAKOBJECTen retrieve (``GET /api/v1/zaakobjecten?zaak=/api/v1/zaken/d4d..2e8``)

**Catalogi API**

* 1x ZAAKTYPE retrieve (``GET /api/v1/zaaktypen/011..3c1``)
* 1x STATUSTYPEn retrieve (``GET /api/v1/statustypen?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 1x BESLUITTYPE retrieve (``GET /api/v1/besluittypen?zaaktype=/api/v1/zaaktypen/011..3c1``)
* 1x RESULTAATTYPE retrieve (``GET /api/v1/resultaattypen/712..a7c?zaaktype=/api/v1/zaaktypen/011..3c1``)

**Documenten API**

* 1x OBJECTINFORMATIEOBJECTen retrieve (``GET /api/v1/objectinformatieobjecten?object=/api/v1/zaken/d4d..2e8``)
* 3x ENKELVOUDIGINFORMATIEOBJECT retrieve (``GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90``)

**Besluiten API**

* 1x BESLUITen retrieve (``GET /api/v1/besluiten?zaak=/api/v1/zaken/d4d..2e8``)

Retrieve history (6)
~~~~~~~~~~~~~~~~~~~~

Retrieve the combined audit trails of a Zaak, Besluit and 3 Documenten from their respective API's.

**Zaken API**

* 1x AUDITTRAIL retrieve (``GET /api/v1/zaken/d4d..2e8/audittrail``)

**Documenten API**

* 3x AUDITTRAIL retrieve (``GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90/audittrail``)

**Besluiten API**

* 1x AUDITTRAIL retrieve (``GET /api/v1/besluiten/a28..6d3/audittrail``)

Create Zaak (7)
~~~~~~~~~~~~~~~

Create a Zaak with its initial Status and a Rol with the person that initiated the
Zaak.

**Zaken API**

* 1x ZAAK create (``POST /api/v1/zaken``)
* 1x STATUS create (``POST /api/v1/status``)
* 1x ROL create (``POST /api/v1/rollen``)

Add Status (8)
~~~~~~~~~~~~~~

**Zaken API**

* 1x STATUS create (``POST /api/v1/status``)

Add Betrokkene (9)
~~~~~~~~~~~~~~~~~~

* *1x Persoon zoeken (buiten scope)*

**Zaken API**

* 1x ROL create (``POST /api/v1/rollen``)

Add Document (10)
~~~~~~~~~~~~~~~~~

Create a Document and make a relation to a Zaak.

**Zaken API**

* 1x ZAAK-INFORMATIEOBJECT create (``POST /api/v1/zaakinformatieobjecten``)

**Documenten API**

* 1x ENKELVOUDIGINFORMATIEOBJECT create (``POST /api/v1/enkelvoudiginformatieobjecten``)

Add Besluit (11)
~~~~~~~~~~~~~~~~

**Besluiten API**

* 1x BESLUIT create (``POST /api/v1/besluiten``)

Add Resultaat (12)
~~~~~~~~~~~~~~~~~~

**Zaken API**

* 1x RESULTAAT create (``POST /api/v1/resultaten``)

Test specificatie
-----------------

Gebruik van scenario's
~~~~~~~~~~~~~~~~~~~~~~

Not every scenario is executed as often. For example, a Zaak is requested more often
than it is created. In the table below, for every 20 x "Retrieve Zaak details"
scenario, 10x "Create Zaak" is executed. This was then converted to a percentage,
assuming that all scenarios represent 100%. We call this the *weight*.

To simulate a user perspective, a specific *waiting time* is introduced after each
scenario. The waiting time represents, for example, the time a user needs to enter data
into the user interface or the time it takes to interpret the data. In the table below,
after executing "Create Zaak", the script waits between 0 and 10 minutes (5 minutes on
average).

Finally, the number of *API-calls* is shown for each scenario.

=== ==============================  ======  ======  ======  ======  ==========
#   Scenario                        Weight          Wait time (m)   API-calls
--- ------------------------------  --------------  --------------  ----------
.   .                               Abs.    %       Avg.    Range   .
=== ==============================  ======  ======  ======  ======  ==========
1   Retrieve Zaken overview         20      20%     2       0 - 4   4
2   ... for a specific Zaaktype     10      10%     2       0 - 4   6
3   Search Zaken by location        1       1%      1       0 - 2   1
4   Search Zaken by person          10      10%     1       0 - 2   1
5   Retrieve Zaak details           8       8%      2       0 - 4   14
6   Retrieve history                2       2%      3       0 - 6   5
7   Create Zaak                     10      10%     5       0 - 10  3
8   Add Status                      20      20%     2       0 - 4   1
9   Add Betrokkene                  3       3%      3       0 - 6   1
10  Add Document                    12      12%     4       0 - 8   2
11  Add Besluit                     2       2%      3       0 - 6   1
12  Add Resultaat                   2       2%      3       0 - 6   1
.   **Total**                       100     100%    31              40
=== ==============================  ======  ======  ======  ======  ==========

If taken the *weight* into account, the overall average *waiting time* is **5 minutes**
and the average number of requests per scenario is **7**.

Virtual users
~~~~~~~~~~~~~

We test with an increasing number of virtual users, from 1 to 100, that concurrently
execute the test scenarios. A virtual user is technically a script that executes the
different scenarios one after another, in the distribution and with the associated
waiting time as shown in the table above.

Testdata
~~~~~~~~

The testset that is present in the database:

* 1.000.000 Zaken in the Zaken API
* 1.000.000 Documenten in the Documenten API
* 1.000.000 Besluiten in the Besluiten API
* 1 Catalogus with 100 Zaaktypen in the Catalogi API
