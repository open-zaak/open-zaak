=========
Open Zaak
=========
*Productiewaardige API's voor Zaakgericht Werken*

`Read this in English`_

.. _`Read this in English`: README.en.md

:Version: 1.7.4
:Source: https://github.com/open-zaak/open-zaak
:Keywords: zaken, zaakgericht werken, zaken-api, catalogi-api, besluiten-api, documenten-api
:PythonVersion: 3.9

|atp| |build-status| |docs| |coverage| |code-quality| |black| |docker|

Deze repository bevat broncode en documentatie voor productiewaardige API's voor Zaakgericht Werken (ZGW). Deze API's volgen de standaard van VNG Realisatie "API's voor Zaakgericht Werken".

Zaakgericht Werken
==================

Zaakgericht werken is een vorm van procesgericht werken die door de Nederlandse gemeenten, en steeds meer landelijke overheden, wordt toegepast om verzoeken van burgers en bedrijven te behandelen. De zaak staat hierbij centraal. Een zaak is een samenhangende hoeveelheid werk met een gedefinieerde aanleiding en een gedefinieerd resultaat waarvan kwaliteit en doorlooptijd bewaakt moeten worden. De API's voor Zaakgericht Werken ondersteunen de registratie van alle metadata en gegevens die komen kijken bij Zaakgericht Werken. Zie ook `Zaakgericht werken in het gemeentelijk gegevenslandschap`_.

.. _`Zaakgericht werken in het gemeentelijk gegevenslandschap`: https://www.gemmaonline.nl/images/gemmaonline/f/f6/20190620_-_Zaakgericht_werken_in_het_Gemeentelijk_Gegevenslandschap_v101.pdf


Standaard "API's voor Zaakgericht Werken"
=========================================

In het kader van Common Ground heeft VNG Realisatie deze standaard ontwikkeld. Daarbij zijn tegelijk met API-specificaties referentie-implementaties gerealiseerd om aan te tonen dat de specificaties in software kunnen worden geïmplementeerd. De volgende inhoudelijke API's maken onderdeel uit van de standaard:

* Catalogi - voor de registratie van zaaktype-catalogi, zaaktype en alle daarbij horende typen.
* Zaken - voor de registratie van zaken. Zaken kunnen o.a. relaties hebben met documenten, besluiten, contacten. De API biedt functionaliteit voor audit trail en archiveren.
* Documenten - voor de registratie van informatieobjecten, hetgeen zowel documenten als andere informatiedragers zoals foto's en film kunnen zijn.
* Besluiten - voor de registratie van besluiten die in het kader van zaakgericht werken worden genomen.

Daarnaast zijn er een paar generieke API's die nodig om gebruik te maken van deze API's:

* Notificaties - in Common Ground worden gegevens bij de bron geregistreerd en bijgehouden. Consumers krijgen niet vanzelf bericht als er iets is gewijzigd. Hiervoor kunnen ze een abonnement registreren bij de Notificaties API.
* Autorisaties - via de Autorisaties API wordt de toegang van applicaties tot gegevens geregeld.

Productiewaardige API's
=======================

Bij de realisatie van productiewaardige API's is aandacht besteed aan een aantal belangrijke aspecten:

* Beheer: er is een beheerportaal ingericht waarmee de verschillende API's door functioneel beheerders kunnen worden beheerd.
* Performance: er zijn performance-metingen verricht op basis van schattingen van de verwachte belasting door applicaties die eindgebruikers gebruiken. Benodigde verbeteringen zijn doorgevoerd waardoor een belasting door 2000 eindgebruikers geen problemen zou moeten opleveren.
* Documentatie van de componenten, met name van de beheer applicaties. (De inhoudelijke documentatie over de API's is onderdeel van de standaard.)
* Uitrol: Om de uitrol naar servers te vereenvoudigen is er een Docker container beschikbaar. Dit zijn een soort componenten die gemakkelijk kunnen worden uitgerold op een server om ze vervolgens in gebruik te nemen. Hiermee kunnen gemeenten de API’s op eenvoudige wijze (laten) draaien bij een hostingpartij.

Architectuur van Open Zaak
==========================

De architectuur van Open Zaak is gebaseerd op een beperkt aantal componenten. De belangrijkste component is de registratiecomponent die de API's voor ZGW aanbiedt. Daarnaast zijn er de volgende componenten:

* Notificatie-component, noodzakelijk voor de werking van Open Zaak.
* Selectielijst component die wordt gebruikt om de VNG Selectielijst voor archiveren te ontsluiten
* Beheerportaal dat toegang biedt tot de verschillende beheerapps die bij de API's horen

.. image:: docs/introduction/_assets/architecture.png
    :width: 100%
    :alt: Open-Zaak Componenten-overzicht

Implementatie
=============

Deze repository bevat de broncode voor de API's. Om gebruik te kunnen maken van de API's moeten deze ergens gehost worden als een service. Als onderdeel van de ontwikkelstraat worden bij elke nieuwe versie van Open Zaak een Docker container die direct kunnen worden uitgerold in een Kubernetes cluster.

Links
=====

* `VNG Standaard API's voor Zaakgericht Werken`_
* `Documentatie`_
* `Docker Hub`_

.. _`Documentatie`: https://open-zaak.readthedocs.io/en/latest/
.. _`Docker Hub`: https://hub.docker.com/u/openzaak
.. _`VNG Standaard API's voor Zaakgericht Werken`: https://github.com/VNG-Realisatie/gemma-zaken

Bouw
====

Deze API's zijn ontwikkeld door `Maykin Media B.V.`_ in opdracht van Amsterdam,
Rotterdam, Utrecht, Tilburg, Arnhem, Haarlem, 's-Hertogenbosch, Delft en een coalitie
van Hoorn, Medemblik, Stede Broec, Drechteland, Enkhuizen (SED), onder regie van `Dimpact`_.

.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _Dimpact: https://www.dimpact.nl

Licentie
========

Licensed under the EUPL_

.. _EUPL: LICENSE.md

.. |build-status| image:: https://github.com/open-zaak/open-zaak/workflows/Run%20CI/badge.svg
    :alt: Build status
    :target: https://github.com/open-zaak/open-zaak/actions?query=workflow%3A%22Run+CI%22

.. |code-quality| image:: https://github.com/open-zaak/open-zaak/workflows/Code%20quality%20checks/badge.svg
     :alt: Code quality checks
     :target: https://github.com/open-zaak/open-zaak/actions?query=workflow%3A%22Code+quality+checks%22

.. |docs| image:: https://readthedocs.org/projects/open-zaak/badge/?version=latest
    :target: https://open-zaak.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/open-zaak/open-zaak/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-zaak

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |docker| image:: https://img.shields.io/docker/image-size/openzaak/open-zaak
    :target: https://hub.docker.com/r/openzaak/open-zaak

.. |atp| image:: https://shields.api-test.nl/endpoint.svg?url=https%3A//api-test.nl/api/v1/provider-latest-badge/14bc91f7-7d8b-4bba-a020-a6c316655e65/
    :target: https://api-test.nl/server/1/6b5fe675-694d-4948-8896-5eae88d30ef0/14bc91f7-7d8b-4bba-a020-a6c316655e65/latest/
