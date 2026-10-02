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

Registraties en API's op basis van de VNG API standaard voor Zaakgericht Werken. (`English version`_)

Ontwikkeld door `Maykin B.V.`_, geïnitieerd door de `Stakeholders`_.

Introductie
===========

Zaakgericht werken is een vorm van procesgericht werken die door de Nederlandse gemeenten, en steeds meer landelijke overheden, wordt toegepast om verzoeken van burgers en bedrijven te behandelen. De zaak staat hierbij centraal. Een zaak is een samenhangende hoeveelheid werk met een gedefinieerde aanleiding en een gedefinieerd resultaat waarvan kwaliteit en doorlooptijd bewaakt moeten worden. De API's voor Zaakgericht Werken ondersteunen de registratie van alle metadata en gegevens die komen kijken bij Zaakgericht Werken. Zie ook `Zaakgericht werken in het gemeentelijk gegevenslandschap`_.

.. _`Zaakgericht werken in het gemeentelijk gegevenslandschap`: https://www.gemmaonline.nl/images/gemmaonline/f/f6/20190620_-_Zaakgericht_werken_in_het_Gemeentelijk_Gegevenslandschap_v101.pdf


Duurzaam beheer
===============

Deze software is open source en vrij te gebruiken binnen de voorwaarden van de EUPL. Veilig en betrouwbaar productiegebruik vraagt echter om structureel beheer, waaronder beveiligingsupdates, dependency- en releasebeheer, kwaliteitsbewaking en het verwerken van kwetsbaarheden. Ook het onderhouden van publieke functies rondom het open source product vraagt om structurele inzet.

**Publieke code vraagt om publieke verantwoordelijkheid.**

De `Stakeholders`_ verwachten van publieke organisaties, die deze software in productie gebruiken, een financiele bijdrage aan de gezamenlijke instandhouding.

Lees meer over de beheerorganisatie, bijdragen en verantwoordelijkheden in `PROJECT_GOVERNANCE.md`_.


API specificaties
=================

Open Zaak bevat meerdere componenten. Hieronder staan per component de API-versies.

==================  ==========  ===================
API-component       API versie  API specificatie
==================  ==========  ===================
Zaken API           1.5.1       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/zaken/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/zaken/openapi.yaml>`_
Documenten API      1.4.2       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/documenten/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/documenten/openapi.yaml>`_
Besluiten API       1.1.0       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/besluiten/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/besluiten/openapi.yaml>`_
Catalogi API        1.3.1       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/catalogi/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/catalogi/openapi.yaml>`_
Autorisaties API    1.0.0       `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/autorisaties/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/1.30.0/src/openzaak/components/autorisaties/openapi.yaml>`_
==================  ==========  ===================

Vorige versies van Open Zaak worden nog 6 maanden ondersteund nadat de volgende versie
is uitgebracht.

Zie: `Alle versies en wijzigingen <https://github.com/maykinmedia/open-zaak/blob/master/CHANGELOG.rst>`_


Component
=========

|build-status| |coverage| |code-quality| |ruff| |python-version|

Open Zaak is bedoeld voor productie-doeleinden maar kan uitgeprobeerd worden door
ontwikkelaars en/of hobbyisten met onderstaande "quickstart".

Quickstart
----------

1. Download en start Open Zaak:

   .. code:: bash

      $ wget https://raw.githubusercontent.com/open-zaak/open-klant/master/docker-compose.yml
      $ docker-compose up -d --no-build
      $ docker-compose exec web src/manage.py createsuperuser

2. In de browser, navigeer naar ``http://localhost:8000/`` om de beheerinterface
   en de API te benaderen.


Links
=====

* `Documentatie <https://open-zaak.readthedocs.io/>`_
* `Docker image <https://hub.docker.com/r/openzaak/open-zaak>`_
* `Issues <https://github.com/open-zaak/open-zaak/issues>`_
* `Code <https://github.com/maykinmedia/open-zaak>`_
* `Community <https://commonground.nl/groups/view/d9c2f667-2f3e-4153-a79b-57dde7f56cc2/open-gegevenslaag-zaken-documenten-producten-klantcontacten>`_


Licentie
========

Copyright © de `Stakeholders`_, 2026

Licensed under the `EUPL`_.

.. _`English version`: README.EN.rst
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
