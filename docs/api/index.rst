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

======================  ============================================================================================================================================================ ================================
API                     Specification version(s)                                                                                                                                     Open Zaak API
======================  ============================================================================================================================================================ ================================
`Zaken API`_            `1.5.1 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/vng-Realisatie/zaken-api/1.5.1/src/openapi.yaml>`__                           `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/zaken/openapi.yaml>`__
`Documenten API`_       `1.6.0 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/documenten-api/1.6.0/src/openapi.yaml>`__                      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/documenten/openapi.yaml>`__
`Catalogi API`_         `1.3.1 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/catalogi-api/1.3.1/src/openapi.yaml>`__                        `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/catalogi/openapi.yaml>`__
`Besluiten API`_        `1.1.0 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/gemma-zaken/master/api-specificatie/brc/1.1.x/openapi.yaml>`__ `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/besluiten/openapi.yaml>`__
`Autorisaties API`_     `1.0.0 <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/autorisaties-api/1.0.0/src/openapi.yaml>`__                    `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/autorisaties/openapi.yaml>`__
======================  ============================================================================================================================================================ ================================

.. _`Zaken API`: https://vng-realisatie.github.io/gemma-zaken/standaard/zaken/
.. _`Documenten API`: https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/
.. _`Catalogi API`: https://vng-realisatie.github.io/gemma-zaken/standaard/catalogi/
.. _`Besluiten API`: https://vng-realisatie.github.io/gemma-zaken/standaard/besluiten/
.. _`Autorisaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/autorisaties/
.. _

In addition, Open Zaak requires access to a `Notificaties API`_. Open Zaak uses
`Open Notificaties`_ by default.

.. _`Notificaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/notificaties/
.. _`Open Notificaties`: https://github.com/open-zaak/open-notificaties


Deviation from the standards
----------------------------

While Open Zaak supports above mentioned standards it also provides extra features, which can enrich
the client experience. The full list of them is documented :ref:`here <api_experimental>`.

Zaken API: expansion depth
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Zaken API 1.6.0 standard allows related resources to be expanded to arbitrary
depth using ``expand``. Open Zaak deviates from this standard: expansion is limited
to explicitly supported paths, with a maximum nesting depth of three levels.
Not every path up to three levels is supported. Refer to the Open Zaak specification
for the allowed ``expand`` values for the operation.

For example, ``hoofdzaak.status.statustype`` spans three levels. When retrieving
zaken, include the parent resources as well::

    ?expand=hoofdzaak,hoofdzaak.status,hoofdzaak.status.statustype

Deeper paths and paths not listed for the operation are not supported.

Reference
---------

.. toctree::
   :maxdepth: 1

   experimental
