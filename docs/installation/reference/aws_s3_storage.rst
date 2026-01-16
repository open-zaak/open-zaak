.. _installation_documenten_aws_s3_storage:

AWS S3 Storage for Documenten API
=================================

By default, Open Zaak stores the contents (``inhoud``) of documents (``EnkelvoudigInformatieObject`` in the API)
on disk. In addition to this, there is also support for using `AWS S3 Storage <https://aws.amazon.com/s3/>`_.

Configuration
-------------

.. warning::

    When switching from filesystem storage to AWS S3 storage for an Open Zaak instance that
    already contains documents, the existing documents must be migrated to the new storage
    manually, as Open Zaak currently does not provide an automatic migration feature.

In order to use AWS S3 Storage, several environment variables must be configured:

* Set ``DOCUMENTEN_API_BACKEND`` to ``aws_s3_storage`` (see :ref:`installation_env_config` > ``Documenten API``)
* See :ref:`installation_env_config` > ``Documenten API AWS S3 Storage`` for the remaining
  variables

To configure authentication, a service principal must be configured in AWS S3.
Follow the `instructions <https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html>`_
to create an app in AWS S3 for Open Zaak.

After configuring an app for Open Zaak, the following environment variables must be set:

**Authentication Settings**:

1. ``AWS_S3_SESSION_PROFILE``: Name of the AWS CLI profile to use for authentication when connecting to AWS S3.
2. ``AWS_S3_ACCESS_KEY_ID``: Access key ID used to authenticate with AWS S3.
3. ``AWS_S3_SECRET_ACCESS_KEY``: Secret access key used together with AWS_S3_ACCESS_KEY_ID to authenticate with AWS S3.
4. ``AWS_SESSION_TOKEN``: Session token used for temporary AWS credentials

**Settings**:

5. ``AWS_STORAGE_BUCKET_NAME``: The name of the S3 bucket that will host the files.
6. ``AWS_LOCATION``: A path prefix that will be prepended to all uploads.

Additional information
----------------------

If this integration is configured, the ``inhoud`` of documents will be stored in AWS S3.
It is important to note that the following files are still stored on disk:

* ``inhoud`` for ``bestandsdelen``: parts of files that are temporarily stored on disk, until
  they are merged into a single large file, after which the temporary files are removed.
* Import metadata and report files for bulk imports (see :ref:`installation_reference_import`).
