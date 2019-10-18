=========
Open Zaak
=========

:Version: 1.0.0-alpha
:Source: https://github.com/open-zaak/open-zaak
:Keywords: zaken, zaakgericht werken, zaken-api, catalogi-api, besluiten-api, documenten-api
:PythonVersion: 3.7

|build-status| |coverage| |black|

API's voor Zaakgericht werken

Ontwikkeld door `Maykin Media B.V.`_ in opdracht van `Dimpact`_.

Inleiding
=========

Binnen het Nederlandse gemeentelandschap wordt zaakgericht werken nagestreefd.
Om dit mogelijk te maken is er gegevensuitwisseling nodig. De kerngegevens van
zaken, documenten en besluiten moeten ergens geregistreerd worden en
opvraagbaar zijn.

**Open Zaak** is een moderne, open source gegevens- en services-laag om
`zaakgericht werken`_ te ondersteunen zoals voorgesteld in de onderste 2 lagen
van het `Common Ground`_ 5-lagen model.

De gegevens worden ontsloten middels een `set API's`_, te weten:

* Zaken API (`Zaken API-specificatie 1.0 RC`_)
* Documenten API (`Documenten API-specificatie 1.0 RC`_)
* Catalogi API (`Catalogi API-specificatie 1.0 RC`_)
* Besluiten API (`Besluiten API-specificatie 1.0 RC`_)
* Autorisatie API (`Autorisaties API-specificatie 1.0 RC`_)

.. _`Common Ground`: https://commonground.nl/
.. _`zaakgericht werken`: https://www.vngrealisatie.nl/ondersteuningsmiddelen/zaakgericht-werken
.. _`set API's`: https://zaakgerichtwerken.vng.cloud/
.. _`Zaken API-specificatie 1.0 RC`: https://zaakgerichtwerken.vng.cloud/standaard/zaken/index
.. _`Documenten API-specificatie 1.0 RC`: https://zaakgerichtwerken.vng.cloud/standaard/documenten/index
.. _`Catalogi API-specificatie 1.0 RC`: https://zaakgerichtwerken.vng.cloud/standaard/catalogi/index
.. _`Besluiten API-specificatie 1.0 RC`: https://zaakgerichtwerken.vng.cloud/standaard/besluiten/index
.. _`Autorisaties API-specificatie 1.0 RC`: https://zaakgerichtwerken.vng.cloud/standaard/autorisaties/index

**Open Zaak** gebruikt de code van de
`referentie implementaties van VNG Realisatie`_ als basis om een stabiele set
API's te realiseren die in productie gebruikt kunnen worden bij gemeenten.

.. _`referentie implementaties van VNG Realisatie`: https://github.com/VNG-Realisatie/gemma-zaken

Licentie
========

Licensed under the EUPL_

.. _EUPL: LICENSE.md
.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _Dimpact: https://www.dimpact.nl

.. |build-status| image:: https://travis-ci.org/open-zaak/open-zaak.svg?branch=master
    :alt: Build status
    :target: https://travis-ci.org/open-zaak/open-zaak

.. |coverage| image:: https://codecov.io/github/open-zaak/open-zaak/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-zaak

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
