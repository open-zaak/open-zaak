.. _api_index:

API-specifications
==================

Open Zaak adheres to the API-specifications as described by the `VNG standards
for "API's voor Zaakgericht werken"`_. The interaction between these API's can
be found there as well.

.. _`VNG standards for "API's voor Zaakgericht werken"`: https://vng-realisatie.github.io/gemma-zaken/

Supported API versions
----------------------

The following API's are available in Open Zaak:

======================  ==========================================
API                     Specification version(s)
======================  ==========================================
`Zaken API`_            `1.5.1 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/vng-Realisatie/zaken-api/1.5.1/src/openapi.yaml>`__
`Documenten API`_       `1.4.2 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/documenten-api/1.4.2/src/openapi.yaml>`__
`Catalogi API`_         `1.3.1 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/catalogi-api/1.3.1/src/openapi.yaml>`__
`Besluiten API`_        `1.1.0 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/gemma-zaken/master/api-specificatie/brc/1.1.x/openapi.yaml>`__
`Autorisaties API`_     `1.0.0 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/autorisaties-api/1.0.0/src/openapi.yaml>`__
======================  ==========================================

.. _`Zaken API`: https://vng-realisatie.github.io/gemma-zaken/standaard/zaken/
.. _`Documenten API`: https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/
.. _`Catalogi API`: https://vng-realisatie.github.io/gemma-zaken/standaard/catalogi/
.. _`Besluiten API`: https://vng-realisatie.github.io/gemma-zaken/standaard/besluiten/
.. _`Autorisaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/autorisaties/

In addition, Open Zaak requires access to a `Notificaties API`_. Open Zaak uses
`Open Notificaties`_ by default.

.. _`Notificaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/notificaties/
.. _`Open Notificaties`: https://github.com/open-zaak/open-notificaties


Deviation from the standards
----------------------------

While Open Zaak supports above mentioned standards it also provides extra features, which can enrich
the client experience. The full list of them is documented :ref:`here <api_experimental>`.

Reference
---------

.. toctree::
   :maxdepth: 1

   experimental
