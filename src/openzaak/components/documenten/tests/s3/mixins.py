# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings
from django.utils.functional import LazyObject

from openzaak.components.documenten.constants import DocumentenBackendTypes

from ...storage import documenten_storage


def upload_to(self, instance, filename):
    return f"uploads/test/{filename}"


class S3torageMixin:
    """
    Mixin to make sure the underlying Documenten storage backend can be overridden
    with `override_settings` to use the S3 storage backend
    """

    s3_overwrite_files = True

    @staticmethod
    def reset_storage():
        assert isinstance(documenten_storage, LazyObject)

        documenten_storage._wrapped = None  # force reload
        documenten_storage._setup()

    def setUp(self):
        super().setUp()

        self.override_settings = override_settings(
            DOCUMENTEN_API_BACKEND=DocumentenBackendTypes.s3_storage,
            AWS_S3_ACCESS_KEY_ID="minioadmin",
            AWS_S3_SECRET_ACCESS_KEY="minioadmin",
            AWS_S3_ENDPOINT_URL="http://localhost:9000",
            AWS_S3_FILE_OVERWRITE=self.s3_overwrite_files,
        )
        self.override_settings.enable()

        self.reset_storage()

        # addCleanup runs in last in, first out order
        self.addCleanup(self.reset_storage)
        self.addCleanup(self.override_settings.disable)
