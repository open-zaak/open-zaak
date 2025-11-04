# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from django.utils.functional import LazyObject

from privates.storages import PrivateMediaFileSystemStorage


class PrivateMediaStorageWithCMIS(LazyObject):  # TODO rename or remove
    def _setup(self):
        self._wrapped = PrivateMediaFileSystemStorage()


private_media_storage_cmis = PrivateMediaStorageWithCMIS()
