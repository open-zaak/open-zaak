.. _development_howtos_s3_storage:

Using S3 storage for Documenten API
=======================================

In order to test S3 storage for the Documenten API locally, make sure the environment
variable ``DOCUMENTEN_API_BACKEND`` is set to ``s3_storage``.

By default, the development and CI settings connect to an S3 server at
``http://localhost:9000``. Locally that is `moto <https://docs.getmoto.org/en/latest/docs/server_mode.html>`_,
a fast S3 mock. Run it without Docker:

.. code-block:: bash

    uvx --from 'moto[server]==5.2.4' moto_server -p 9000
    curl -X PUT http://localhost:9000/openzaak  # create the bucket

or with Docker, which creates the bucket for you:

.. code-block:: bash

    docker compose -f docker/docker-compose.s3.yml up -d

moto accepts any credentials and keeps everything in memory, so after a restart the
bucket and its files are gone, while the database still refers to them.

.. note::

    MinIO was used before, but its community edition is abandoned and its images are
    no longer published. `RustFS <https://github.com/rustfs/rustfs>`_ looks promising
    as a persistent, MinIO-like alternative. `Silo <https://silo.pigsty.io/>`_ is a
    community fork of MinIO that is a drop-in replacement, but it is young and
    maintained by a single organisation.

If you want to connect with a real S3 storage instance, make sure to follow the instructions
in the :ref:`installation docs <installation_documenten_s3_storage>` to configure
an app and service principal in S3 and then set the correct values as described for the
envvars.

(Re)-recording VCR cassettes
----------------------------

The S3 tests replay VCR cassettes, which are recorded against the server described above.
To (re)-record a cassette, make sure the server is running, delete the cassette and run
its test with ``VCR_RECORD_MODE=once``:

.. code-block:: bash

    rm src/openzaak/components/documenten/tests/s3/files/vcr_cassettes/SmallFileUpload/test_update_eio_put.yaml
    VCR_RECORD_MODE=once pytest src/openzaak/components/documenten/tests/s3/test_upload.py -k test_update_eio_put

Don't use ``VCR_RECORD_MODE=all`` on an existing cassette: it appends the new recording to
the old one instead of replacing it.

.. note::

    When making requests to the S3 storage API, the filename is included in the
    request URL, which can cause issues with VCR, because it matches by method + URL.
    Some extra work is needed to make sure that the same filename is
    used in each test (e.g. specifying explicit ``inhoud__filename`` or mocking ``uuid``
    to make it a fixed value for a specific tests).
