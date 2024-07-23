.. _installation_reference_import:

===========================
Importing documents in bulk
===========================

Open Zaak data can be supplied in various ways. One can of course make API calls,
for example to create ``EnkelvoudigInformatieObject``'s but whenever a large amount
of data needs to be created in a relatively short time period, this can become
a not-so-pleasant experience. To prevent having to deal with these kinds of situations,
Open Zaak users can make use of the import functionality for ``EnkelvoudigInformatieObject``'s.
Open Zaak exposes several API endpoints (which are not part of the Documenten API standard)
to help aid the user to import larger amounts of ``EnkelvoudigInformatieObject``'s.

Configuration
--------------

Environment variables related to the import functionality are also described in :ref:`Environment configuration reference <installation_env_config>`

* ``IMPORT_DOCUMENTEN_BASE_DIR`` is used to determine the absolute import path for each
  row in the import metadata file. All file paths specified in the import metadata
  file should be relative to the directory specified for this setting.
  By default this is the same directory as the projects directory (``BASE_DIR``) and
  can either be configured through an environment variable or directly through the
  django's settings file being used.
* ``IMPORT_DOCUMENTEN_BATCH_SIZE`` is the number of rows that will be processed at a time.
* ``IMPORT_RETENTION_DAYS``: an integer which specifies the number of days after which ``Import`` instances will be deleted

Process
-------

The import process consists of several steps with each step having an API endpoint.
The process consists of the following steps:

1. Creating the ``Import``
2. Uploading the ``Import`` metadata file
3. (Optionally) Retrieving the status of the ``Import``
4. (Optionally) Retrieving the report file of the ``Import``
5. (Optionally) Deleting the ``Import``

An visual representation of the process can be seen below:
.. image:: sequence-diagram.png

**Permissions**

Importing ``EnkelvoudigInformatieObjecten`` is not possible for all authenticated users
for Open Zaak. The reasoning behind this is that not all users, for example have
the rights to create ``EnkelvoudigInformatieObjecten`` with certain
``InformatieObjectType``'s. Various permissions exist within Open Zaak and
therefore to make use of the import functionality, only users with an
``Applicatie`` with the ``heeft_alle_autorisaties`` set to ``True`` are allowed
to perform any import operation.

**Creating an Import**

The first step in the import process is that of making an ``Import`` resource.
This is done through a ``POST`` request. The request body of this request can be empty
for this step.

Creating an ``Import`` is only possible whenever no other ``Import`` instance exist
with the statusses ``pending`` or ``active``.

Whenever no other import is ``pending`` or ``active``, the endpoint will provide the user
three URLs: a URL to upload an import metadata file, a URL to retrieve the status
of an import and another URL for downloading a report of the import. These three
urls provide the user the ability to progress further in the import process.
After this request the ``Import`` instance will have it's status changed to
``pending``.

See the `API documentation`_ for more details.

**Starting an Import**

After creating an `Import` instance, users can upload an import metadata file. This
should be a CSV which consists of rows with the data needed to create an
``EnkelvoudigInformatieObject``. This data is roughly the same as the data needed
for creating an ``EnkelvoudigInformatieObject`` through a "regular" API call
with some exceptions. For more details about the format and the requirements of
the CSV file, the API documentation should be consulted. The request for this
endpoint should be a ``POST`` request containing the CSV data in its request body.

Whenever the CSV file contains invalid and/or missing headers, the import process will
not be started and the error response will contain any missing headers.

The ``bestandspad`` column, which is required for each row in the CSV file,
is the path to the file which will be imported and will be assosciated to the
``EnkelvoudigInformatieObject``. This should be a relative path from the directory
configured in ``IMPORT_DOCUMENTEN_BASE_DIR``.

The import will only start if the ``IMPORT_DOCUMENTEN_BASE_DIR`` setting is set
correctly. Unknown directories or the ``IMPORT_DOCUMENTEN_BASE_DIR`` leading to a
a file instead of a directory are examples of incorrect configurations. An
incorrectly configured ``IMPORT_DOCUMENTEN_BASE_DIR`` setting will cause the import
to not start.

Just like in the step to create the ``Import`` instance, no other ``pending`` or
``active`` import instances can be active before starting the specified ``Import``.

After this request passes validation (with the above mentioned checks) the
actual import process is started through a background task and the status of the
``Import`` instance is changed to ``active``.

See the `API documentation`_ for more details.

**Retrieving the status**

The status of the ``Import`` can be retrieved when an import process is started
and has the status ``pending``, ``active``, ``finished`` or ``error``. This endpoint
can be called through a `GET` request. The data of the response contains
information, for example, about the total amount of rows the import metadata file
has and the amount of rows the ``Import`` at that time has processed.

If the background task is finished the status of the ``Import`` is either ``finished``
or ``error`` in case of unrecoverable error situations.

See the `API documentation`_ for more details.

**Retrieving a report file**

When an ``Import`` instance is ``finished`` or has an ``error``, a report
file of the process can be downloaded. This report is a CSV file the same as
the provided metadata file with an additional two columns that specify whether
a row was imported successfully and if there any comments about the row.

See the `API documentation`_ for more details.

**Deleting an Import**

When an ``Import`` instance has the status ``finished``, ``error`` or ``pending``
it can be deleted. Deletion of ``Import`` instances that are older than the environment
variable ``IMPORT_RENTENTION_DAYS`` days and have one of the above mentioned
statuses is done in the background through a daily occurring task.

See the `API documentation`_ for more details.

Import behavior
----------------

The import process is a background task and imports each row in
batches (configured through ``IMPORT_DOCUMENTEN_BATCH_SIZE``). During each batch,
a validation error can occur, for example an existing ``uuid`` being present in the
database. This will not cause other rows to not be imported.

If a row does not cause any validation errors, the file associated with that
row will be copied to Open Zaak's storage. If the file already exists there,
it will be overwritten.

Another situation can occur where the import process cannot proceed, for example
a database connection loss. This will stop the import process
(the background task). In this situation the database cannot be reached and the
data of the ``Import`` instance (e.g statistics) will be out-of-sync. However, logging
is done and the report file will have comments for all rows in that
specified batch.

It is **important** to note that **no notifications** will be sent during or
after the import process. If you use the import process please notify the subscribers of your API about the new documents. so they won't have inconsistent data.

Examples
---------

The following steps are an example of how the import process could look like.
For these examples the `curl` tool is used.

**Creating an import**

.. code-block:: bash

    curl --request POST \
         --header "Authorization: Bearer <token>" \
         https://<domain-name>/documenten/api/v1/import/create


**Starting an import**

.. code-block:: bash

    curl --request POST \
         --header "Authorization: Bearer <token>" \
         --header "Content-Type: text/csv" \
         --upload-file <path-to-metadata-file> \
         https://<domain-name>/documenten/api/v1/import/<import-uuid>/upload


**Retrieving the status of an import**

.. code-block:: bash

    curl --request GET \
         --header "Authorization: Bearer <token>" \
         https://<domain-name>/documenten/api/v1/import/<import-uuid>/status


**Retrieving the report of an import**

.. code-block:: bash

    curl --request GET \
         --header "Authorization: Bearer <token>" \
         https://<domain-name>/documenten/api/v1/import/<import-uuid>/report


**Deleting an import**

.. code-block:: bash

    curl --request DELETE \
         --header "Authorization: Bearer <token>" \
         https://<domain-name>/documenten/api/v1/import/<import-uuid>/delete


.. _API documentation: https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-zaak/main/src/openzaak/components/documenten/openapi.yaml
