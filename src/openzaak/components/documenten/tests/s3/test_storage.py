# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, tag

from maykin_common.vcr import VCRMixin

from ...storage import documenten_storage
from .mixins import S3torageMixin, upload_to


@tag("gh-2282", "s3-storage")
@patch("privates.fields.PrivateMediaFileField.generate_filename", upload_to)
class S3torageTests(VCRMixin, S3torageMixin, TestCase):
    def test_storage_configuration(self):
        self.assertIsNotNone(documenten_storage)

        self.assertEqual(
            documenten_storage.bucket_name, settings.AWS_STORAGE_BUCKET_NAME
        )
        self.assertEqual(documenten_storage.region_name, settings.AWS_S3_REGION_NAME)
        self.assertEqual(documenten_storage.endpoint_url, "http://localhost:9000")

        connection = documenten_storage.connection
        self.assertEqual(
            connection.meta.client._request_signer._credentials.access_key, "minioadmin"
        )
        self.assertEqual(
            connection.meta.client._request_signer._credentials.secret_key, "minioadmin"
        )

    def test_storage_url_file(self):
        file_path = "uploads/test/file.txt"
        url = documenten_storage.url(file_path)
        self.assertIn("AWSAccessKeyId=minioadmin", url)
        self.assertIn("Expires=", url)
        self.assertIn("Signature=", url)
