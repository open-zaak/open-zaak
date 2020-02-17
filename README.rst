=========
Open Zaak
=========

:Version: 1.0.1
:Source: https://github.com/open-zaak/open-zaak
:Keywords: zaken, zaakgericht werken, zaken-api, catalogi-api, besluiten-api, documenten-api
:PythonVersion: 3.7

|build-status| |docs| |coverage| |black| |docker|

API's voor Zaakgericht werken

Ontwikkeld door `Maykin Media B.V.`_ in opdracht van Amsterdam, Rotterdam,
Utrecht, Tilburg, Arnhem, Haarlem, 's-Hertogenbosch, Delft en Hoorn,
Medemblik, Stede Broec, Drechteland, Enkhuizen (SED), onder regie van
`Dimpact`_.

Inleiding
=========

Binnen het Nederlandse gemeentelandschap wordt zaakgericht werken nagestreefd.
Om dit mogelijk te maken is er gegevensuitwisseling nodig. De kerngegevens van
zaken, documenten en besluiten moeten ergens geregistreerd worden en
opvraagbaar zijn.

**Open Zaak** is een moderne, open source gegevens- en services-laag om
`zaakgericht werken`_ te ondersteunen zoals voorgesteld in de onderste 2 lagen
van het `Common Ground`_ 5-lagen model.

De gegevens worden ontsloten middels een `gestandaardiseerde set VNG API's`_,
te weten:

* Zaken API (`Zaken API-specificatie 1.0`_)
* Documenten API (`Documenten API-specificatie 1.0`_)
* Catalogi API (`Catalogi API-specificatie 1.0`_)
* Besluiten API (`Besluiten API-specificatie 1.0`_)
* Autorisaties API (`Autorisaties API-specificatie 1.0`_)

De `Notificaties API`_ is nodig voor **Open Zaak** en is beschikbaar via
`Open Notificaties`_.

.. _`Common Ground`: https://commonground.nl/
.. _`zaakgericht werken`: https://www.vngrealisatie.nl/ondersteuningsmiddelen/zaakgericht-werken
.. _`gestandaardiseerde set VNG API's`: https://zaakgerichtwerken.vng.cloud/
.. _`Zaken API-specificatie 1.0`: https://zaakgerichtwerken.vng.cloud/standaard/zaken/index
.. _`Documenten API-specificatie 1.0`: https://zaakgerichtwerken.vng.cloud/standaard/documenten/index
.. _`Catalogi API-specificatie 1.0`: https://zaakgerichtwerken.vng.cloud/standaard/catalogi/index
.. _`Besluiten API-specificatie 1.0`: https://zaakgerichtwerken.vng.cloud/standaard/besluiten/index
.. _`Autorisaties API-specificatie 1.0`: https://zaakgerichtwerken.vng.cloud/standaard/autorisaties/index
.. _`Notificaties API`: https://zaakgerichtwerken.vng.cloud/standaard/notificaties/index
.. _`Open Notificaties`: https://github.com/open-zaak/open-notificaties

**Open Zaak** gebruikt de code van de
`referentie implementaties van VNG Realisatie`_ als basis om een stabiele set
API's te realiseren die in productie gebruikt kunnen worden bij gemeenten.

.. _`referentie implementaties van VNG Realisatie`: https://github.com/VNG-Realisatie/gemma-zaken

Links
=====

* `Documentatie`_
* `Docker Hub`_

.. _`Documentatie`: https://open-zaak.readthedocs.io/en/latest/
.. _`Docker Hub`: https://hub.docker.com/u/openzaak

Licentie
========

Licensed under the EUPL_

.. _EUPL: LICENSE.md
.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _Dimpact: https://www.dimpact.nl

.. |build-status| image:: https://travis-ci.org/open-zaak/open-zaak.svg?branch=master
    :alt: Build status
    :target: https://travis-ci.org/open-zaak/open-zaak

.. |docs| image:: https://readthedocs.org/projects/open-zaak/badge/?version=latest
    :target: https://open-zaak.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/open-zaak/open-zaak/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-zaak

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |docker| image:: https://images.microbadger.com/badges/image/openzaak/open-zaak.svg
    :target: https://microbadger.com/images/openzaak/open-zaak
