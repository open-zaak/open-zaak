# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from typing import cast

from django.conf import settings
from django.core.files.storage import Storage
from django.utils.functional import LazyObject

from privates.storages import PrivateMediaFileSystemStorage
from storages.backends.azure_storage import (
    AzureStorage as _AzureStorage,
    AzureStorageFile as _AzureStorageFile,
)


class AzureStorageFile(_AzureStorageFile):
    pass


class AzureStorage(_AzureStorage):
    def path(self, name: str) -> str:
        # TODO is this correct?
        return self._get_valid_path(name)


class DocumentenStorage(LazyObject):
    def _setup(self):
        if settings.DOCUMENTEN_API_USE_AZURE_BLOB_STORAGE:
            self._wrapped = AzureStorage()
        else:
            self._wrapped = PrivateMediaFileSystemStorage()


documenten_storage = cast(Storage, DocumentenStorage())
