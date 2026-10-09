# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""

import base64
from datetime import date
from io import BytesIO
from unittest.mock import patch
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, tag

from freezegun import freeze_time
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..constants import MAX_INHOUD_FILENAME_LENGTH, MAX_UPLOAD_INHOUD_FILENAME_LENGTH
from ..models import EnkelvoudigInformatieObject
from ..storage import documenten_storage
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from .utils import get_operation_url


@temp_private_root()
class US39TestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create_enkelvoudiginformatieobject(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
            "identificatie": "AMS20180701001",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "text_extra.txt",
            "auteur": "ANONIEM",
            "formaat": "text/plain",
            "taal": "dut",
            "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(eio.identificatie, "AMS20180701001")
        self.assertEqual(eio.creatiedatum, date(2018, 7, 1))

        download_url = urlparse(response.data["inhoud"])

        self.assertEqual(
            download_url.path,
            get_operation_url("enkelvoudiginformatieobject_download", uuid=eio.uuid),
        )
        self.assertEqual(eio.canonical.latest_version, eio)

    @tag("gh-2530")
    def test_post_inhoud_validates_generated_filename(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        data = {
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "test",
            "auteur": "ANONIEM",
            "taal": "dut",
            "inhoud": base64.b64encode(b"document").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{reverse(informatieobjecttype)}",
        }

        # Base64 uploads get a generated filename rather than a client filename.
        with patch(
            "openzaak.components.documenten.api.serializers.AnyBase64File.get_file_name",
            return_value="a" * (MAX_INHOUD_FILENAME_LENGTH - 4),
        ):
            response = self.client.post(
                get_operation_url("enkelvoudiginformatieobject_create"), data
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        document = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(
            document.inhoud.name.rsplit("/", 1)[-1],
            f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH + 4)}.bin",
        )
        self.assertEqual(document.inhoud.read(), b"document")

    def test_read_detail_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue().decode("utf-8"), "some data")

    @override_settings(DOCUMENTEN_API_BACKEND="test")
    def test_read_detail_file_not_implemented_documenten_api_backend(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_list_file(self):
        EnkelvoudigInformatieObjectCanonicalFactory.create()
        eio = EnkelvoudigInformatieObject.objects.get()
        list_url = get_operation_url("enkelvoudiginformatieobject_list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["results"]
        download_url = urlparse(data[0]["inhoud"])

        self.assertEqual(
            download_url.path,
            get_operation_url("enkelvoudiginformatieobject_download", uuid=eio.uuid),
        )

    def test_delete_eio_deletes_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud=File(BytesIO(b"some data"), name="some-file2.bin"),
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        file_path = eio.inhoud.path

        self.assertTrue(documenten_storage.exists(file_path))

        response = self.client.delete(reverse(eio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(documenten_storage.exists(file_path))


@temp_private_root()
@tag("gh-2530")
class EIOInhoudFilenameTests(TestCase):
    def setUp(self):
        super().setUp()
        self.canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

    def build_document(self, upload):
        return EnkelvoudigInformatieObjectFactory.build(
            canonical=self.canonical,
            informatieobjecttype=self.informatieobjecttype,
            inhoud=upload,
        )

    def test_uploaded_filenames_are_validated_and_saved(self):
        cases = (
            ("report.pdf", "report.pdf"),  # Standard filename
            (
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)}.pdf",
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)}.pdf",
            ),  # Filename at the expected length
            (
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)}a.pdf",
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)}.pdf",
            ),  # Filename exceeding the limit by one character
            (
                f"{'a' * (MAX_INHOUD_FILENAME_LENGTH - 4)}.pdf",
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)}.pdf",
            ),  # Maximum-length PDF filename
            (
                f"{'a' * (MAX_INHOUD_FILENAME_LENGTH - 5)}.docx",
                f"{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 5)}.docx",
            ),  # Maximum-length DOCX filename, truncated to the upload limit
            (
                f"test.{'a' * (MAX_INHOUD_FILENAME_LENGTH - 9)}.pdf",
                f"test.{'a' * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 9)}.pdf",
            ),  # Preserve filename prefix and extension when truncating
            (
                "a" * MAX_INHOUD_FILENAME_LENGTH,
                "a" * MAX_UPLOAD_INHOUD_FILENAME_LENGTH,
            ),  # Filename without an extension at the maximum length
        )

        build = self.build_document

        for filename, expected_name in cases:
            with self.subTest(model=build.__name__, filename=filename):
                document = build(SimpleUploadedFile(filename, b"document"))

                document.full_clean()
                self.assertEqual(document.inhoud.name, expected_name)
                document.save()
                document.refresh_from_db()

                self.assertLessEqual(
                    len(document.inhoud.name.rsplit("/", 1)[-1]),
                    MAX_INHOUD_FILENAME_LENGTH,
                )
                self.assertEqual(document.inhoud.read(), b"document")

    def test_duplicate_filenames_do_not_overwrite_files(self):
        name = "a" * (MAX_UPLOAD_INHOUD_FILENAME_LENGTH - 4)
        filename = f"{'a' * (MAX_INHOUD_FILENAME_LENGTH - 4)}.pdf"
        build = self.build_document
        with self.subTest(model=build.__name__):
            first = build(SimpleUploadedFile(filename, b"first upload"))
            first.full_clean()
            first.save()
            second = build(SimpleUploadedFile(filename, b"second upload"))
            second.full_clean()
            second.save()
            first.refresh_from_db()
            second.refresh_from_db()

            self.assertEqual(first.inhoud.name.rsplit("/", 1)[-1], f"{name}.pdf")
            second_name = second.inhoud.name.rsplit("/", 1)[-1]
            self.assertTrue(
                second_name.startswith(f"{name}_")
            )  # duplicate name will have _
            self.assertTrue(second_name.endswith(".pdf"))
            self.assertEqual(len(second_name), MAX_INHOUD_FILENAME_LENGTH)
            self.assertEqual(first.inhoud.read(), b"first upload")
            self.assertEqual(second.inhoud.read(), b"second upload")

    def test_filename_over_limit_is_rejected(self):
        build = self.build_document
        with self.subTest(model=build.__name__):
            upload = SimpleUploadedFile("test.pdf", b"document")
            # UploadedFile normally truncates names before model validation.
            upload._name = "a" * (MAX_INHOUD_FILENAME_LENGTH + 1)
            document = build(upload)

            with self.assertRaises(ValidationError) as context:
                document.full_clean()

            self.assertEqual(
                context.exception.message_dict["inhoud"],
                [
                    "De bestandsnaam van de inhoud mag niet langer zijn dan 255 tekens, inclusief de extensie."
                ],
            )
            self.assertIsNone(document.pk)

    @freeze_time("2026-10-01T12:00:00")
    def test_stored_filename_is_unchanged(self):
        build = self.build_document
        with self.subTest(model=build.__name__):
            filename = f"{'a' * (MAX_INHOUD_FILENAME_LENGTH - 4)}.pdf"
            document = build(SimpleUploadedFile(filename, b"document"))

            document.save()
            document.refresh_from_db()
            filename = document.inhoud.name

            document.full_clean()
            document.save()
            document.refresh_from_db()

            self.assertIn("/2026/10/", filename)
            self.assertEqual(document.inhoud.name, filename)
            self.assertEqual(document.inhoud.read(), b"document")
