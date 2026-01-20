# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from typing import cast

from django.conf import settings
from django.core.files.storage import Storage
from django.utils.functional import LazyObject

import structlog
from azure.core.exceptions import AzureError
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from botocore.exceptions import EndpointConnectionError
from privates.storages import PrivateMediaFileSystemStorage
from storages.backends.azure_storage import AzureStorage as _AzureStorage
from storages.backends.s3 import S3Storage as _S3Storage

from openzaak.components.documenten.constants import DocumentenBackendTypes

logger = structlog.stdlib.get_logger(__name__)


class S3Storage(_S3Storage):
    def connection_check(self) -> bool:
        """
        Checks if the storage backend is reachable and credentials are valid.
        """
        try:
            self.connection.meta.client.list_buckets()
            return True
        except EndpointConnectionError:
            logger.exception("endpoint_connection_error")
        except Exception:
            logger.exception("failed_connection_check")
        return False

    def path(self, name: str) -> str:
        return self.get_available_name(name)


class AzureStorage(_AzureStorage):
    def get_default_settings(self):
        _settings = super().get_default_settings()
        _settings.setdefault("client_options", {})
        _settings["client_options"]["retry_total"] = 0

        # Make use of authentication through a service principal, if the necessary
        # envvars are configured
        if (
            settings.AZURE_TENANT_ID
            and settings.AZURE_CLIENT_ID
            and settings.AZURE_CLIENT_SECRET
        ):
            _settings["token_credential"] = ClientSecretCredential(
                tenant_id=settings.AZURE_TENANT_ID,
                client_id=settings.AZURE_CLIENT_ID,
                client_secret=settings.AZURE_CLIENT_SECRET,
            )

            # In django-storages, `connection_string` takes precedence over all other
            # auth methods, but authenticating through a service principal is the
            # preferred method, so we let that take precedence here instead
            _settings["connection_string"] = None
        return _settings

    def _get_service_client(self):
        """
        The original implementation of `_get_service_client` does not use the
        AZURE_API_OPTIONS setting when specifying a connection string, which makes it
        impossible to override the Azure API version when using a connection string
        """
        if self.connection_string is not None:
            options = self.client_options
            return BlobServiceClient.from_connection_string(
                self.connection_string, **options
            )
        return super()._get_service_client()

    def path(self, name: str) -> str:
        return self._get_valid_path(name)

    def connection_check(self) -> bool:
        """
        Method to validate that connection can be made with Azure blob storage
        """
        try:
            self.exists("dummy-file.txt")
        except AzureError:
            logger.exception("could_not_connect_with_azure_storage")
            return False
        return True


class DocumentenStorage(LazyObject):
    def _setup(self):
        match settings.DOCUMENTEN_API_BACKEND:
            case DocumentenBackendTypes.azure_blob_storage:
                self._wrapped = AzureStorage()
            case DocumentenBackendTypes.s3_storage:
                self._wrapped = S3Storage()
            case DocumentenBackendTypes.filesystem | _:
                self._wrapped = PrivateMediaFileSystemStorage()

    def connection_check(self):
        if hasattr(self._wrapped, "connection_check"):
            return self._wrapped.connection_check()
        return True  # PrivateMediaFileSystemStorage


documenten_storage = cast(Storage, DocumentenStorage())
