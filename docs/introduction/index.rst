.. _introduction_index:

Introduction
============

**Open Zaak** is a modern, open-source data- and services-layer to enable
`zaakgericht werken`_, a Dutch alternative to case management. Open Zaak offers
structured data storage and services that implement the `VNG standards for
"API's voor Zaakgericht werken"`_ in line with the `Common Ground`_ model.

.. _`Common Ground`: https://commonground.nl/
.. _`zaakgericht werken`: https://www.vngrealisatie.nl/ondersteuningsmiddelen/zaakgericht-werken
.. _`VNG standards for "API's voor Zaakgericht werken"`: https://zaakgerichtwerken.vng.cloud/

Open Zaak exposes several :ref:`API's<api_index>` to store and retrieve data:

* Zaken API (case instances)
* Documenten API (documents)
* Catalogi API (case types)
* Besluiten API (decisions)
* Autorisaties API (authorizations)

The `Notificaties API`_ is required for Open Zaak to work but is available as
a separate package, `Open Notificaties`_.

.. _`Notificaties API`: https://zaakgerichtwerken.vng.cloud/standaard/notificaties/index
.. _`Open Notificaties`: https://github.com/open-zaak/open-notificaties

**Open Zaak** is based on the `API reference implementations by VNG Realisatie`_
to create a production-grade product that can be used by municipalities.

.. _`API reference implementations by VNG Realisatie`: https://github.com/VNG-Realisatie/gemma-zaken
.. _`Documentatie`: https://open-zaak.readthedocs.io/en/latest/


.. toctree::
   :maxdepth: 1
   :caption: Further reading

   architecture
   team
   open-source/index
