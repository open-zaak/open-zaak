Architecture
============

**Open Zaak** is based on the `reference implementation of the "API's voor
Zaakgericht werken"`_ made by `VNG Realisatie`_. The overall architecture
remains faithful to the `Common Ground`_ principles and all API specifications.

The architecture of **Open Zaak** focusses on excellent performance, optimal
stability and to guarantee data integrity.

To that end, **Open Zaak** combines the "API's voor Zaakgericht werken" that
are essentially tightly coupled, into a single product. This allows for major
performance improvements since related objects (like a `BESLUIT` for a `ZAAK`)
do not need to fetched over the network but can be directly obtained from the
database. This also guarantees data integrity on database level, rather than on
service (API) level.

In addition, **Open Zaak** uses caching wherever possible to prevent needless
requests over the netwerk to fetch data from external API's. Data integrity can
not be guaranteed on database level when relations are created to external
API's. In this case, data integrity is enforced on service level as much as
possible.

The use of external API's is fully supported in **Open Zaak**, even for API's
that are also offered by **Open Zaak** itself. For example, a `ZAAK` in
**Open Zaak**, available via the `Zaken API` can have a `DOCUMENT` that is
accessible via an external `Documenten API` from another vendor. The only
requirement is that all API's adhere to `VNG standards for "API's voor
Zaakgericht werken"`_.

No permanent copies are made of original sources in **Open Zaak** as dictated
by the `Common Ground`_ principles.

Overview
--------

.. image:: _assets/architecture.png
    :width: 100%
    :alt: Architectural overview of component inside and related to Open Zaak.

.. _reference implementation of the "API's voor Zaakgericht werken": https://github.com/VNG-Realisatie/gemma-zaken
.. _VNG Realisatie: https://www.vngrealisatie.nl/
.. _Common Ground: https://commonground.nl/
.. _`VNG standards for "API's voor Zaakgericht werken"`: https://zaakgerichtwerken.vng.cloud/
