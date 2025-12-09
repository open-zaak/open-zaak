# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings
from django.utils.functional import LazyObject

from ...storage import documenten_storage


class AzureBlobStorageMixin:
    """
    Mixin to make sure the underlying Documenten storage backend can be overridden
    with `override_settings` to use the Azure storage backend
    """

    azure_overwrite_files = True

    @staticmethod
    def reset_storage():
        assert isinstance(documenten_storage, LazyObject)

        documenten_storage._wrapped = None  # force reload
        documenten_storage._setup()

    def setUp(self):
        super().setUp()

        self.override_settings = override_settings(
            DOCUMENTEN_API_USE_AZURE_BLOB_STORAGE=True,
            AZURE_OVERWRITE_FILES=self.azure_overwrite_files,
        )
        self.override_settings.enable()

        self.reset_storage()

        # addCleanup runs in last in, first out order
        self.addCleanup(self.reset_storage)
        self.addCleanup(self.override_settings.disable)
