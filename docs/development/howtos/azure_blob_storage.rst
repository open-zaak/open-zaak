.. _development_howtos_azure_storage:

Using Azure blob storage for Documenten API
===========================================

In order to test Azure blob storage for the Documenten API locally, make sure the environment
variable ``DOCUMENTEN_API_USE_AZURE_BLOB_STORAGE`` is set to ``true``.

By default, the development and CI settings are configured to use a connection string to
connect with `Azurite <https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite>`_.
You can spin up Azurite with:

.. code-block::

    docker compose -f docker/docker-compose.azurite.yml up -d

If you want to connect with a real Azure storage instance, make sure to follow the instructions
in the :ref:`installation docs <installation_documenten_azure_blob_storage>` to configure
an app and service principal in Azure and then set the correct values as described for the
envvars.

(Re)-recording VCR cassettes
----------------------------

The same Azurite docker compose setup as described above is used together with VCR in the
testsuite. To (re)-record cassettes, make sure Azurite is running, delete the existing cassettes
or set ``VCR_RECORD_MODE=all`` and run the tests.

.. note::

    When making requests to the Azure storage API, the filename is included in the
    request URL, which can cause issues with VCR, because it matches by method + URL.
    Some extra work is needed to make sure that the same filename is
    used in each test (e.g. specifying explicit ``inhoud__filename`` or mocking ``uuid``
    to make it a fixed value for a specific tests).
