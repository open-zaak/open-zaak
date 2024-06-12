.. _installation_reference_containers:

Importing documenten
=======================

Open Zaak data can be supplied in various ways. One can ofcourse make API calls
for example to create `EnkelvoudigInformatieObject`'s but whenever a large amount
of data needs to be created in a relatively short time period this can become
a not-so-pleasant experience. To prevent having to deal with these kinds of situations
Open Zaak users can make use of the import functionality for `EnkelvoudigInformatieObject`'s.
Open Zaak exposes several API endpoints to help aid the user to import larger amounts
of `EnkelvoudigInformatieObject`'s.

Process
-------

The import process consists of several steps with each step having a API endpoint.
The process consists of the following steps:

1. Creating the `Import`
2. Uploading the `Import` metadata file
3. (Optionally) Retrieving the status of the `Import`
4. (Optionally) Retrieving the report file of the `Import`

**Permissions**

Importing `EnkelvoudigInformatieObjecten` is not possible for all authenticated users
for Open Zaak. The reasoning behind this is that not all users for example have
the rights to create `EnkelvoudigInformatieObjecten` with certain `InformatieObjectType`'s.
Various permissions exist within Open Zaak and therefore to make use of the import
functionality, users only with the `heeft_alle_autorisaties` set to `True` are allowed
to perform any import operation.

**Creating an Import**

The first step in the import process is that of making an `Import` resource.
This is done through a `POST` request. The request body of this request can be empty
for this step.

Creating an `Import` is only possible whenever no other `Import` instance exist
with the statusses `pending` or `active`.

Whenever no other import is pending or active, the endpoint will provide the user
three urls; an url to upload an import metadata file, an url to retrieve the status
of an import and another url for downloading a report of the import. These three
urls provide the user the ability to progress further in the import process.

The next step in the import process, after creating an `Import` instance, is providing
a metadata file which starts the actual importing of `EnkelvoudigInformatieObject`'s.

**Starting an Import**

After creating an `Import` instance, users can provide an import metadafile. This
should be a csv which consists of rows with data needed to create an `EnkelvoudigInformatieObject`.
The data this csv should contain is rougly the same as that is needed for creating
an `EnkelvoudigInformatieObject` through a "regular" API call with some exceptions.
For more details about the format and the requirements of the csv file, the API
documentation should be consulted. The request for this endpoint should be a `POST`
request containing the csv data in its request body.

Whenever the csv contains invalid and or missing headers the import process will
not be started. Whenever headers are missing the error response will contain those
headers.

One column which is required for each row in the csv file is the path to the
file which will be imported and will be assosiated to the `EnkelvoudigInformatieObject`.
This should be a relative path from the path configured in `IMPORT_DOCUMENTEN_BASE_DIR`.

Before starting an import, the directory configured through `IMPORT_DOCUMENTEN_BASE_DIR`,
is accessed to check if this directory exists (and if it actually is a directory).
Whenever this is not the case the import also will not start.

Just like in the step to create the `Import` instance, no other `pending` or `active`
import instances can be active before starting the specified `Import`.

Whenever this request passes validation (with the above mentioned checks) the
actual import process is started through a background task.

**Retrieving the status**

Whenever an `Import` instance has the status `pending`, `active`, `finished` or
`error` and the import process is started, the status of that `Import` can be
retrieved. This endpoint can be called through a `GET` request. The data of the
response contains information for example about the total amount of rows the
import metadata file has and the amount of rows the `Import` at that time has
processed. See the API documentation of this endpoint for more information.

**Retrieving a report file**

Whenever an `Import` instance has the status `finished` or `error` an report
file can be downloaded of the process. This report is a csv almost identical to
that of the provided metadata file with the additional columns which specify wether
an row is imported or not and if there any comments about the row.

Import behavior
----------------

The actual import process, which is a background task, imports each row in
batches (configured through `IMPORT_DOCUMENTEN_BATCH_SIZE`). During each batch
several error situations can occure. For example an existing
`EnkelvoudigInformatieObject` can exist with the specified `uuid`. This can be
considered a validation error and will not cause other rows in the specific batch
not to be imported.

Another situation that can occure is for example a database connection loss. This
causes an situation where the import process cannot proceed and will stop the import
process (the background task). In this situation the database cannot be reached and
the data `Import` instance will be out-of-sync. Logging however is done and the
report file will have comments for all rows in that specified batch.

During the import, files are copied to the import path that the "regular" endpoint
for `EnkelvoudigInformatieObject`'s would do so too. Files are however overwritten
whenever they already exist.

Configuration
--------------

Settings related to the import functionaly are:
- `IMPORT_DOCUMENTEN_BASE_DIR`
- `IMPORT_DOCUMENTEN_BATCH_SIZE`

`IMPORT_DOCUMENTEN_BASE_DIR` is used to determine the absolute import path for each
row in the import metadata file. All file paths specified in the import metadata
file should be relative to the directory specified for this setting.
By default this is the same directory as the projects directory (`BASE_DIR`) and
can either be configured through an environment variable or directly through the
django's settings file being used.

`IMPORT_DOCUMENTEN_BATCH_SIZE` is used to split the amount of data which will be
processed at a time. This setting was added for performance reasons and can be
tweaked accordingly through an environment variable or directly through the django's
setting file being used.


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
