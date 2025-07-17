.. _scripts:

Scripts
=======

Dump data
---------

Met het script `dump_data.sh` kan de data van alle componenten (zaken, documenten...) worden geëxporteerd naar een sql bestand.

Standaard wordt naast het volledige schema alle catalogi, zaak, besluit & document data. Om alleen specifieke data te exporteren kunnen de gewenste component namen worden meegegeven:

.. code-block:: shell

    /dump_data.sh zaken documenten

.. note::

    om een postgres 17 db te exporteren is de package postgres-client-17 vereist.

Environment variabelen
----------------------

* DB_HOST (db)
* DB_PORT (5432)
* DB_USER (postgres)
* DB_NAME (postgres)
* DB_PASSWORD ("")
* DUMP_FILE ("dump_$(date +'%Y-%m-%d_%H-%M-%S').sql")

.. code-block:: shell

    DB_HOST=localhost DB_NAME=openzaak ./bin/dump_data.sh
