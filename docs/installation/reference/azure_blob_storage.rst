.. _installation_documenten_azure_blob_storage:

Azure Blob Storage for Documenten API
=====================================

By default, Open Zaak stores the contents (``inhoud``) of documents (``EnkelvoudigInformatieObject`` in the API)
on disk. In addition to this, there is also support for using `Azure blob storage <https://azure.microsoft.com/en-us/products/storage/blobs>`_.

Configuration
-------------

.. warning::

    When switching from filesystem storage to Azure storage for an Open Zaak instance that
    already contains documents, the existing documents must be migrated to the new storage
    manually, as Open Zaak currently does not provide an automatic migration feature.

In order to use Azure blob storage, several environment variables must be configured,
see :ref:`installation_env_config` > ``Documenten API Azure Blob Storage``.

To configure authentication, a service principal must be configured in Azure.
Follow the `instructions <https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser>`_
to create an app in Azure for Open Zaak. After configuring an app for Open Zaak,
the following environment variables must be set:

1. ``AZURE_ACCOUNT_NAME``: the name of the storage account that will be used.
2. ``AZURE_CLIENT_ID``: copy the value of ``Application (client) ID`` under ``Overview``.
3. ``AZURE_TENANT_ID``: copy the value of ``Directory (tenant) ID`` under ``Overview``.
4. ``AZURE_CLIENT_SECRET``: navigate to ``Manage > Certificates & secrets`` and create a new client secret, then copy the value of that secret.

In addition to this, the app needs permission to read, write and delete blobs in Azure Storage.
This can be done as follows:

1. Navigate to the storage account that will be used in Azure.
2. Click on ``Access Control (IAM)`` and then ``Add`` > ``Add role assignment``.
3. Search for ``Storage Blob Data Contributor`` and select that role, click ``Next``.
4. Choose ``Assign access to`` > ``User, group or service principal`` and then ``Select members``.
5. Search for the name of the created app and select it.
6. Click ``Review + assign`` to assign the role.

It may take up to a minute before Open Zaak actually can access the Azure storage API.

Additional information
----------------------

If this integration is configured, the ``inhoud`` of documents will be stored in Azure.
It is important to note that the following files are still stored on disk:

* ``inhoud`` for ``bestandsdelen``: parts of files that are temporarily stored on disk, until
  they are merged into a single large file, after which the temporary files are removed.
* Import metadata and report files for bulk imports (see :ref:`installation_reference_import`).
