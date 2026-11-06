# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

import os
from typing import cast

from django.conf import settings
from django.core.files.storage import Storage, storages
from django.utils.functional import LazyObject

import structlog
from azure.core.exceptions import AzureError
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from botocore.exceptions import ClientError
from privates.storages import STORAGE_ALIAS as PRIVATE_MEDIA_STORAGE_ALIAS
from storages.backends.azure_storage import AzureStorage as _AzureStorage
from storages.backends.s3 import S3Storage as _S3Storage

from openzaak.components.documenten.constants import DocumentenBackendTypes

from .exceptions import DocumentBackendNotImplementedError

logger = structlog.stdlib.get_logger(__name__)


def _if_none_match(params, **kwargs):
    params.setdefault("IfNoneMatch", "*")


class S3Storage(_S3Storage):
    """
    S3 storage that doesn't overwrite objects unless ``file_overwrite`` is set.

    ``get_available_name`` only checks if a name is free; an object only exists once
    its upload is complete, so concurrent saves with the same name would all pick
    it and overwrite each other. The upload is made conditional instead, and retried
    with an alternative name if another save claimed the name first.
    """

    file_overwrite: bool  # set from AWS_S3_FILE_OVERWRITE by django-storages

    @property
    def connection(self):
        is_new = getattr(self._connections, "connection", None) is None
        connection = super().connection
        if is_new and not self.file_overwrite:
            # s3transfer doesn't pass `IfNoneMatch` from `upload_fileobj`'s ExtraArgs,
            # so it's added to the requests directly. Once it does, this can be
            # replaced by adding it in `_get_write_parameters`. See:
            # https://github.com/boto/boto3/issues/4366
            # https://github.com/boto/s3transfer/pull/371
            assert connection.meta is not None
            events = connection.meta.client.meta.events
            for operation in ["PutObject", "CompleteMultipartUpload"]:
                events.register(
                    f"before-parameter-build.s3.{operation}",
                    _if_none_match,
                    unique_id=f"openzaak-if-none-match-{operation}",
                )
        return connection

    def _save(self, name, content):
        while True:
            try:
                return super()._save(name, content)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                if self.file_overwrite or code not in {
                    "PreconditionFailed",  # another upload completed
                    "ConditionalRequestConflict",  # another upload is completing
                }:
                    raise
                dir_name, file_name = os.path.split(name)
                file_root, file_ext = os.path.splitext(file_name)
                name = self.get_available_name(
                    os.path.join(
                        dir_name, self.get_alternative_name(file_root, file_ext)
                    )
                )

    def connection_check(self) -> bool:
        """
        Checks if the storage backend is reachable and credentials are valid.
        """
        try:
            self.connection.meta.client.list_buckets()
            return True
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
            case DocumentenBackendTypes.filesystem:
                self._wrapped = get_private_media_storage()
            case _:
                raise DocumentBackendNotImplementedError(
                    settings.DOCUMENTEN_API_BACKEND
                )

    def connection_check(self):
        if hasattr(self._wrapped, "connection_check"):
            return self._wrapped.connection_check()
        return True  # PrivateMediaStorage


def get_private_media_storage() -> Storage:
    return storages[PRIVATE_MEDIA_STORAGE_ALIAS]


documenten_storage = cast(Storage, DocumentenStorage())
