# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.conf import settings
from django.core.files.base import ContentFile
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


@tag("gh-2592", "s3-storage")
class S3ConcurrentSaveTests(VCRMixin, S3torageMixin, TestCase):
    s3_overwrite_files = False  # the Open Zaak default

    # VCR matches requests on URL, which contains the alternative name
    @patch("django.core.files.storage.base.get_random_string", return_value="gh2592a")
    def test_concurrent_saves_with_the_same_name_do_not_overwrite_each_other(
        self, _get_random_string
    ):
        """
        Two documents with the same name, saved at the same time, must end up in
        different objects; or one of them must fail explicitly.
        """
        name = "uploads/test/besluit.txt"
        documenten_storage.delete(name)
        storage = documenten_storage._wrapped
        get_available_name = storage.get_available_name
        saved = {}
        racing = True

        def get_available_name_and_save_second(name, max_length=None):
            nonlocal racing
            available = get_available_name(name, max_length=max_length)
            if racing:
                racing = False
                # the second save completes after the first one picked its name,
                # but before the first one's upload finished
                saved["second"] = storage.save(name, ContentFile(b"second"))
            return available

        with patch.object(
            storage, "get_available_name", get_available_name_and_save_second
        ):
            saved["first"] = storage.save(name, ContentFile(b"first"))

        for key in saved:
            self.addCleanup(storage.delete, saved[key])

        for key in ["first", "second"]:
            with self.subTest(key), storage.open(saved[key], "rb") as f:
                self.assertEqual(f.read(), key.encode())
        self.assertNotEqual(saved["first"], saved["second"])
