# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from freezegun import freeze_time

from openzaak.components.documenten.constants import DocumentenBackendTypes
from openzaak.components.documenten.exceptions import DocumentBackendNotImplementedError
from openzaak.components.documenten.models import EnkelvoudigInformatieObject

from ..fields import get_default_path


@freeze_time("2026-01-01T12:00:00")
class TestFieldUtils(SimpleTestCase):
    def test_get_default_path(self):
        with self.subTest("test AzureStorage"):
            with override_settings(
                DOCUMENTEN_API_BACKEND=DocumentenBackendTypes.azure_blob_storage
            ):
                field = EnkelvoudigInformatieObject.inhoud.field
                field.storage._setup()
                assert get_default_path(field) == Path("uploads/2026/01")

        with self.subTest("test S3 Storage"):
            with override_settings(
                DOCUMENTEN_API_BACKEND=DocumentenBackendTypes.s3_storage
            ):
                field = EnkelvoudigInformatieObject.inhoud.field
                field.storage._setup()
                assert get_default_path(field) == Path("uploads/2026/01")

        with self.subTest("test Filesystem Storage"):
            with override_settings(
                DOCUMENTEN_API_BACKEND=DocumentenBackendTypes.filesystem
            ):
                field = EnkelvoudigInformatieObject.inhoud.field
                field.storage._setup()
                path = get_default_path(field)
                assert str(path).endswith(
                    f"{settings.PRIVATE_MEDIA_URL}uploads/2026/01"
                )

        with self.subTest("test not implemented documenten API backend"):
            with override_settings(DOCUMENTEN_API_BACKEND="test"):
                with self.assertRaises(DocumentBackendNotImplementedError):
                    field = EnkelvoudigInformatieObject.inhoud.field
                    field.storage._setup()
                    get_default_path(field)
