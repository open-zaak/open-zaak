=========
Open Zaak
=========

.. image:: https://raw.githubusercontent.com/open-zaak/open-zaak/refs/heads/main/.github/assets/open-zaak-logo.svg
    :height: 100px
    :alt: Open Zaak

:Version: 1.30.0
:Source: https://github.com/open-zaak/open-zaak
:Keywords: zaken, zaakgericht werken, zaken-api, catalogi-api, besluiten-api, documenten-api
:PythonVersion: 3.12

|docs| |docker|

Registrations and API's based on the VNG API standard for Zaakgericht Werken. (`Nederlandse versie`_)

Developed by `Maykin B.V.`_, initiated by the `Stakeholders`_.

Introductie
===========

Case-oriented working ("Zaakgericht werken") is a form of process-oriented working adopted by Dutch municipalities - and increasingly by national government bodies - to handle requests from citizens and businesses. The case ("zaak") is central to this approach. A case is a coherent body of work with a defined trigger and a defined outcome, requiring the monitoring of both quality and turnaround time. The API's for "Zaakgericht werken" support the recording of all metadata and data associated with this way of working. Also see: `Zaakgericht werken in het gemeentelijk gegevenslandschap`_.

.. _`Zaakgericht werken in het gemeentelijk gegevenslandschap`: https://www.gemmaonline.nl/images/gemmaonline/f/f6/20190620_-_Zaakgericht_werken_in_het_Gemeentelijk_Gegevenslandschap_v101.pdf


Sustainable Management
======================

This software is open source and free to use under the terms of the EUPL. However, safe and reliable use in a production environment requires structured management, including security updates, dependency and release management, quality assurance, and vulnerability handling. Maintaining public-facing functions associated with the open-source product also requires a sustained commitment.

**Public code calls for public responsibility.**

The `Stakeholders`_ expect public organizations, using this software in production, to make a financial contribution towards its collective maintenance.

Read more about the management organization, contributions, and responsibilities in `PROJECT_GOVERNANCE.md`_.


API specifications
==================

Open Zaak contains multiple components. Below, you will find the API-version per
component. 

==================  ============  ===================
API-component       API version   API specification
==================  ============  ===================
Zaken API           1.5.1         `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/zaken/openapi.yaml>`_,
                                  `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/zaken/openapi.yaml>`_
Documenten API      1.4.2       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/documenten/openapi.yaml>`_,
                                  `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/documenten/openapi.yaml>`_
Besluiten API       1.1.0         `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/besluiten/openapi.yaml>`_,
                                  `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/besluiten/openapi.yaml>`_
Catalogi API        1.3.1         `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/catalogi/openapi.yaml>`_,
                                  `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/catalogi/openapi.yaml>`_
Autorisaties API    1.0.0         `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/autorisaties/openapi.yaml>`_,
                                  `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/autorisaties/openapi.yaml>`_
==================  ============  ===================

Previous versions of Open Zaak are supported for 6 month after the next version is
released.

See: `All versions and changes <https://github.com/open-zaak/open-zaak/blob/master/CHANGELOG.rst>`_


Component
=========

|build-status| |coverage| |code-quality| |ruff| |python-version|

Open Zaak is meant for production use but can be tried out by developers or enthousiastsusing the quickstart below.

Quickstart
----------

1. Download and start Open Zaak:

   .. code:: bash

      $ wget https://raw.githubusercontent.com/open-zaak/open-klant/master/docker-compose.yml
      $ docker-compose up -d --no-build
      $ docker-compose exec web src/manage.py createsuperuser

2. In the browser, navigate to ``http://localhost:8000/`` to access the admin
   and the API.


References
==========

* `Documentation <https://open-zaak.readthedocs.io/>`_
* `Docker image <https://hub.docker.com/r/openzaak/open-zaak>`_
* `Issues <https://github.com/open-zaak/open-zaak/issues>`_
* `Code <https://github.com/maykinmedia/open-zaak>`_
* `Community <https://commonground.nl/groups/view/d9c2f667-2f3e-4153-a79b-57dde7f56cc2/open-gegevenslaag-zaken-documenten-producten-klantcontacten>`_


Licence
=======

Copyright © de `Stakeholders`_, 2026

Licensed under the `EUPL`_.

.. _`Nederlandse versie`: README.NL.rst
.. _`Maykin B.V.`: https://www.maykin.nl
.. _`Stakeholders`: STAKEHOLDERS.md
.. _`PROJECT_GOVERNANCE.md`: PROJECT_GOVERNANCE.md
.. _`EUPL`: LICENSE.md


.. |build-status| image:: https://github.com/open-zaak/open-zaak/actions/workflows/ci.yml/badge.svg?branch=main
    :alt: Build status
    :target: https://github.com/open-zaak/open-zaak/actions/workflows/ci.yml

.. |code-quality| image:: https://github.com/open-zaak/open-zaak/actions/workflows/code_quality.yml/badge.svg?branch=main
     :alt: Code quality checks
     :target: https://github.com/open-zaak/open-zaak/actions/workflows/code_quality.yml

.. |docs| image:: https://readthedocs.org/projects/open-zaak/badge/?version=latest
    :target: https://open-zaak.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/open-zaak/open-zaak/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-zaak

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

.. |python-version| image:: https://img.shields.io/badge/python-3.12-blue.svg
    :alt: Supported Python version

.. |docker| image:: https://img.shields.io/docker/image-size/openzaak/open-zaak
    :target: https://hub.docker.com/r/openzaak/open-zaak
