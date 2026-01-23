.. _installation_documenten_s3_storage:

S3 Storage for Documenten API
=============================

By default, Open Zaak stores the contents (``inhoud``) of documents (``EnkelvoudigInformatieObject`` in the API)
on disk. In addition, Open Zaak also supports **S3 Storage**.

.. note::

    S3 Storage is a standard supported by multiple storage systems:

    * AWS S3
    * Backblaze B2
    * Cloudflare R2
    * Digital Ocean
    * Oracle Cloud
    * Scaleway

Configuration
-------------

.. warning::

    When switching from filesystem storage to **S3 Storage** for an Open Zaak instance that
    already contains documents, the existing documents must be migrated to the new storage
    manually, as Open Zaak currently does not provide an automatic migration feature.

In order to use S3 Storage, several environment variables must be configured:

* Set ``DOCUMENTEN_API_BACKEND`` to ``s3_storage`` (see :ref:`installation_env_config` > ``Documenten API``)
* See :ref:`installation_env_config` > ``Documenten API S3 Storage`` for the remaining variables

**Authentication Settings**:

1. ``S3_SESSION_PROFILE``: Name of the CLI profile to use for authentication when connecting to S3 storage.
2. ``S3_ACCESS_KEY_ID``: Access key ID used to authenticate with S3 storage.
3. ``S3_SECRET_ACCESS_KEY``: Secret access key used together with S3_ACCESS_KEY_ID to authenticate to S3 storage.
4. ``S3_SESSION_TOKEN``: Session token used for temporary S3 credentials.

For more information, please refer to the documentation of the S3-compatible system for authentication configuration:
`django-storages S3-compatible systems <https://django-storages.readthedocs.io/en/latest/backends/s3_compatible/index.html#>`_.

**Storage Settings**:

5. ``S3_STORAGE_BUCKET_NAME``: The name of the S3 bucket that will host the files.
6. ``S3_LOCATION``: A path prefix that will be prepended to all uploads.

Additional Information
----------------------

When this integration is configured, the ``inhoud`` of documents will be stored on S3.
However, the following files are still stored on the local filesystem:

* ``inhoud`` of ``bestandsdelen``: temporary parts of files that are stored locally until merged into a single large file; temporary files are then deleted.
* Metadata and report files for bulk imports (see :ref:`installation_reference_import`).
