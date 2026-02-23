# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import shutil
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.test import RequestFactory, TestCase, override_settings, tag
from django.utils import timezone

from maykin_common.vcr import VCRMixin
from privates.test import temp_private_root
from vng_api_common.fields import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse
from vng_api_common.utils import generate_unique_identification

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.constants import (
    ChecksumAlgoritmes,
    OndertekeningSoorten,
    Statussen,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.storage import documenten_storage
from openzaak.components.documenten.tasks import _import_document_row
from openzaak.components.documenten.tests.factories import (
    DocumentRowFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.import_data.tests.utils import ImportTestMixin
from openzaak.utils import build_absolute_url
from openzaak.utils.fields import get_default_path

from ..mixins import S3torageMixin, upload_to


@temp_private_root()
@tag("gh-2282", "s3-storage")
@override_settings(ALLOWED_HOSTS=["testserver"])
@patch("privates.fields.PrivateMediaFileField.generate_filename", upload_to)
class ImportDocumentRowTests(S3torageMixin, ImportTestMixin, VCRMixin, TestCase):
    clean_documenten_files = True
    clean_import_files = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.request_factory = RequestFactory()
        cls.request = cls.request_factory.get("/")

        cls.catalogus = CatalogusFactory.create()
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        cls.catalogus_url = build_absolute_url(
            reverse(cls.catalogus), request=cls.request
        )
        cls.informatieobjecttype_url = build_absolute_url(
            reverse(cls.informatieobjecttype), request=cls.request
        )

        now = timezone.now()
        cls.creatiedatum = now.date()

    def setUp(self):
        super().setUp()
        # Mock this to ensure the upload_to folder is used

        self.field = EnkelvoudigInformatieObject.inhoud.field
        self.old_value = self.field.upload_to
        self.field.upload_to = "uploads/test/"

    def tearDown(self):
        self.field.upload_to = self.old_value
        super().tearDown()

    def test_minimum_fields(self):
        import_file_path = Path("import-test-files/foo.txt")
        import_file_content = b"minimum fields"
        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        assert eio is not None
        self.assertIsInstance(eio, EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.informatieobjecttype, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        self.assertEqual(eio.inhoud.read(), import_file_content)
        # assert that it's stored in S3
        self.assertTrue(documenten_storage.exists(str(imported_path)))
        # Make sure the LOCATION is not prepended twice
        self.assertFalse(str(imported_path).startswith("documenten/documenten"))
        # assert the file does not exist on disk
        self.assertFalse(imported_path.exists())

    def test_all_fields(self):
        zaak = ZaakFactory()

        creatiedatum = date(2024, 1, 1)

        uuid = uuid4()
        identificatie = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=creatiedatum), "creatiedatum"
        )
        import_file_path = Path("import-test-files/foobar.txt")

        import_file_content = b"all fields"

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            uuid=str(uuid),
            identificatie=identificatie,
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar.value,
            formaat="Formaat Y",
            auteur="Auteur Y",
            status=Statussen.definitief.value,
            taal="nld",
            bestandsnaam="foobar.txt",
            bestandsomvang="8092",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            beschrijving="a very nice document",
            ontvangstdatum=str(date(2024, 1, 1)),
            verzenddatum=str(date(2024, 1, 1)),
            indicatie_gebruiksrecht="false",
            verschijningsvorm="form XYZ",
            ondertekening_soort=OndertekeningSoorten.analoog.value,
            ondertekening_datum=str(date(2024, 1, 1)),
            integriteit_algoritme=ChecksumAlgoritmes.crc_16.value,
            integriteit_waarde="foo",
            integriteit_datum=str(date(2024, 1, 1)),
            informatieobjecttype=self.informatieobjecttype_url,
            zaak_uuid=str(zaak.uuid),
            trefwoorden='"foo,bar"',
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(
            row, 0, identifier, [], {str(zaak.uuid): zaak.pk}, self.request
        )

        eio = document_row.instance

        assert eio is not None
        self.assertIsInstance(eio, EnkelvoudigInformatieObject)

        self.assertEqual(eio.uuid, str(uuid))
        self.assertEqual(eio.identificatie, identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(
            eio.vertrouwelijkheidaanduiding, VertrouwelijkheidsAanduiding.openbaar
        )
        self.assertEqual(eio.formaat, "Formaat Y")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.status, Statussen.definitief)
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.bestandsnaam, "foobar.txt")
        self.assertEqual(eio.bestandsomvang, 8092)
        self.assertEqual(eio.beschrijving, "a very nice document")
        self.assertEqual(eio.ontvangstdatum, date(2024, 1, 1))
        self.assertEqual(eio.verzenddatum, date(2024, 1, 1))
        self.assertEqual(eio.verschijningsvorm, "form XYZ")
        self.assertEqual(
            eio.ondertekening,
            {
                "soort": OndertekeningSoorten.analoog,
                "datum": date(2024, 1, 1),
            },
        )

        self.assertEqual(
            eio.integriteit,
            {
                "algoritme": ChecksumAlgoritmes.crc_16,
                "datum": date(2024, 1, 1),
                "waarde": "foo",
            },
        )
        self.assertEqual(eio.informatieobjecttype, self.informatieobjecttype)
        self.assertEqual(eio.trefwoorden, ["foo", "bar"])
        self.assertEqual(eio.inhoud.read(), import_file_content)
        # assert that it's stored
        self.assertTrue(documenten_storage.exists(str(imported_path)))
        # assert the file does not exist on disk
        self.assertFalse(imported_path.exists())

    def test_upload_dir_does_not_exist(self):
        """
        Test that the files are correctly copied to the upload dir even tough it
        does not exist yet
        """
        import_file_path = Path("import-test-files/foo2.txt")
        import_file_content = b"minimum fields"

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        shutil.rmtree(default_imported_file_path, ignore_errors=True)

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        assert eio is not None
        self.assertIsInstance(eio, EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.informatieobjecttype, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        self.assertEqual(eio.inhoud.read(), import_file_content)
        # assert that it's stored
        self.assertTrue(documenten_storage.exists(str(imported_path)))
        # assert the file does not exist on disk
        self.assertFalse(imported_path.exists())

    def test_lower_column_count(self):
        import_file_path = Path("import-test-files/foo3.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(
            row[:5], 0, identifier, [], {}, self.request
        )

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("insufficient column count", document_row.comment)

        default_file_path = get_default_path(self.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())
        self.assertFalse(documenten_storage.exists(str(file_path)))

    def test_validation_error(self):
        import_file_path = Path("import-test-files/foo4.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="foobar",  # Incorrect date
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("creatiedatum", document_row.comment)

        default_file_path = get_default_path(self.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())
        self.assertFalse(documenten_storage.exists(str(file_path)))

    def test_invalid_uuid(self):
        import_file_path = Path("import-test-files/foo5.txt")

        row = DocumentRowFactory(
            uuid="invalid-uuid",
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("not a valid UUID (version 4)", document_row.comment)

        default_file_path = get_default_path(self.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())
        self.assertFalse(documenten_storage.exists(str(file_path)))

    def test_existing_uuid(self):
        existing_eio = EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=self.informatieobjecttype_url,
            inhoud__filename="test_existing_uuid.bin",
        )

        import_file_path = Path("import-test-files/foo6.txt")

        default_file_path = get_default_path(self.field)

        row = DocumentRowFactory(
            uuid=str(existing_eio.uuid),
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(
            row, 0, identifier, [str(existing_eio.uuid)], {}, self.request
        )

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("was already found", document_row.comment)
        self.assertIn("Not overwriting existing EIO", document_row.comment)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())
        self.assertFalse(documenten_storage.exists(str(file_path)))

    def test_unknown_zaak_uuid(self):
        import_file_path = Path("import-test-files/foo7.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype_url,
            zaak_uuid="b0f3681d-945a-4b30-afcb-12cad0a3eeaf",
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertEqual(
            document_row.comment, "Zaak ID specified for row 0 is unknown."
        )

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())
        self.assertFalse(documenten_storage.exists(str(imported_path)))

    def test_non_existent_file(self):
        import_file_path = Path("import-test-files/foo8.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
            ignore_import_path=True,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("does not exist", document_row.comment)

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())
        self.assertFalse(documenten_storage.exists(str(imported_path)))

    def test_directory_as_path(self):
        import_file_path = Path("import-test-files/foobar/")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            is_dir=True,
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("is not a file", document_row.comment)

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())
        self.assertFalse(documenten_storage.exists(str(imported_path)))

    @patch("openzaak.components.documenten.tasks.copy_file_to_storage")
    def test_unable_to_copy_file(self, patched_copy):
        patched_copy.side_effect = FileNotFoundError

        import_file_path = Path("import-test-files/foo9.txt")

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("Unable to copy file for row", document_row.comment)

        self.assertFalse(imported_path.exists())
        self.assertFalse(documenten_storage.exists(str(imported_path)))

    def test_invalid_host_header(self):
        import_file_path = Path("import-test-files/foo10.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(self.field)

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        request = self.request_factory.get("/", headers={"Host": "foobar.com"})

        document_row = _import_document_row(row, 0, identifier, [], {}, request)

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("Unable to import line", document_row.comment)

        self.assertFalse(imported_path.exists())
        self.assertFalse(documenten_storage.exists(str(imported_path)))


@tag("gh-2282", "s3-storage")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ImportDocumentRowWithoutOverwriteTests(
    S3torageMixin, ImportTestMixin, VCRMixin, TestCase
):
    clean_documenten_files = True
    clean_import_files = True
    s3_overwrite_files = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.request_factory = RequestFactory()
        cls.request = cls.request_factory.get("/")

        cls.catalogus = CatalogusFactory.create()
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        cls.catalogus_url = build_absolute_url(
            reverse(cls.catalogus), request=cls.request
        )
        cls.informatieobjecttype_url = build_absolute_url(
            reverse(cls.informatieobjecttype), request=cls.request
        )

        now = timezone.now()
        cls.creatiedatum = now.date()

    def setUp(self):
        super().setUp()
        # Mock this to ensure the upload_to folder is used

        self.field = EnkelvoudigInformatieObject.inhoud.field
        self.old_value = self.field.upload_to
        self.field.upload_to = "uploads/test/"

    def tearDown(self):
        self.field.upload_to = self.old_value
        super().tearDown()

    # Mock this to ensure the requests made to S3 match the cassettes
    @patch("django.core.files.storage.base.get_random_string", return_value="1234567")
    def test_file_already_exists_in_storage(self, _):
        import_file_path = Path("import-test-files/already_exists.txt")
        import_file_content = b"already exists"

        default_imported_file_path = get_default_path(self.field)

        existing_file_path = Path(default_imported_file_path) / import_file_path.name

        # Make sure the file already exists in S3 storage
        documenten_storage.save(str(existing_file_path), BytesIO(import_file_content))

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(existing_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype_url,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        assert eio is not None
        self.assertIsInstance(eio, EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.informatieobjecttype, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        self.assertEqual(eio.inhoud.read(), import_file_content)

        actual_file_path = eio.inhoud.file.name

        # assert that it's stored
        self.assertTrue(documenten_storage.exists(str(existing_file_path)))
        self.assertTrue(documenten_storage.exists(actual_file_path))
        # Make sure the LOCATION is not prepended twice
        self.assertFalse(str(actual_file_path).startswith("documenten/documenten"))
        # assert the file does not exist on disk
        self.assertFalse(existing_file_path.exists())

        # The actual file path of the import will be different, because a file already
        # existed at the specified path
        self.assertNotEqual(str(existing_file_path), actual_file_path)
        self.assertTrue(
            actual_file_path.startswith("uploads/test/already_exists_1234567")
        )
