.. _development_howtos_s3_storage:

Using S3 storage for Documenten API
=======================================

In order to test S3 storage for the Documenten API locally, make sure the environment
variable ``DOCUMENTEN_API_BACKEND`` is set to ``s3_storage``.

By default, the development and CI settings are configured to use a connection string to
connect with `MinIO <https://docs.min.io/enterprise/aistor-object-store/developers/s3-api-compatibility/>`_.
You can spin up MinIO with:

.. code-block::

    docker compose -f docker/docker-compose.minio.yml up -d

If you want to connect with a real S3 storage instance, make sure to follow the instructions
in the :ref:`installation docs <installation_documenten_s3_storage>` to configure
an app and service principal in S3 and then set the correct values as described for the
envvars.

(Re)-recording VCR cassettes
----------------------------

The same MinIO docker compose setup as described above is used together with VCR in the
testsuite. To (re)-record cassettes, make sure MinIO is running, delete the existing cassettes
or set ``VCR_RECORD_MODE=all`` and run the tests.

.. note::

    When making requests to the S3 storage API, the filename is included in the
    request URL, which can cause issues with VCR, because it matches by method + URL.
    Some extra work is needed to make sure that the same filename is
    used in each test (e.g. specifying explicit ``inhoud__filename`` or mocking ``uuid``
    to make it a fixed value for a specific tests).
