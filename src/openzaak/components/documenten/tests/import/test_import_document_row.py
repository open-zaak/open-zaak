# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

import requests_mock
from vng_api_common.fields import VertrouwelijkheidsAanduiding
from vng_api_common.utils import generate_unique_identification
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.documenten.constants import (
    ChecksumAlgoritmes,
    OndertekeningSoorten,
    Statussen,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.tasks import _import_document_row
from openzaak.components.documenten.tests.factories import (
    DocumentRowFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import (
    get_catalogus_response,
    get_informatieobjecttype_response,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.import_data.tests.utils import ImportTestMixin
from openzaak.tests.utils.mocks import MockSchemasMixin
from openzaak.utils.fields import get_default_path


@override_settings(ALLOWED_HOSTS=["testserver"])
class ImportDocumentRowTests(ImportTestMixin, MockSchemasMixin, TestCase):
    mocker_attr = "requests_mock"

    clean_documenten_files = True
    clean_import_files = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        cls.informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        now = timezone.now()
        cls.creatiedatum = now.date()

        cls.request_factory = RequestFactory()

        cls.request = cls.request_factory.get("/")

    def setUp(self):
        self.requests_mock = requests_mock.Mocker()
        self.requests_mock.start()

        self.requests_mock.get(
            self.informatieobjecttype,
            json=get_informatieobjecttype_response(
                self.catalogus, self.informatieobjecttype
            ),
        )
        self.requests_mock.get(
            self.catalogus,
            json=get_catalogus_response(self.catalogus, self.informatieobjecttype),
        )

        self.addCleanup(self.requests_mock.stop)

        super().setUp()

    def test_minimum_fields(self):
        import_file_path = Path("import-test-files/foo.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIs(type(eio), EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio._informatieobjecttype_url, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        with open(imported_path) as file:
            self.assertEqual(file.read(), import_file_content)

    def test_all_fields(self):
        zaak = ZaakFactory()

        creatiedatum = date(2024, 1, 1)

        uuid = uuid4()
        identificatie = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=creatiedatum), "creatiedatum"
        )
        import_file_path = Path("import-test-files/foobar.txt")
        import_file_content = "all fields"

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

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
            informatieobjecttype=self.informatieobjecttype,
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

        self.assertIs(type(eio), EnkelvoudigInformatieObject)

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
        self.assertEqual(eio._informatieobjecttype_url, self.informatieobjecttype)
        self.assertEqual(eio.trefwoorden, ["foo", "bar"])

        with open(imported_path) as file:
            self.assertEqual(file.read(), import_file_content)

    def test_upload_dir_does_not_exist(self):
        """
        Test that the files are correctly copied to the upload dir even tough it
        does not exist yet
        """
        import_file_path = Path("import-test-files/foo.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

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
            informatieobjecttype=self.informatieobjecttype,
        )

        identifier = generate_unique_identification(
            EnkelvoudigInformatieObject(creatiedatum=self.creatiedatum), "creatiedatum"
        )

        document_row = _import_document_row(row, 0, identifier, [], {}, self.request)

        eio = document_row.instance

        self.assertIs(type(eio), EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio._informatieobjecttype_url, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        with open(imported_path) as file:
            self.assertEqual(file.read(), import_file_content)

    def test_lower_column_count(self):
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

        self.assertIn("insufficient row count", document_row.comment)

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_validation_error(self):
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="foobar",  # Incorrect date
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_invalid_uuid(self):
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            uuid="invalid-uuid",
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_existing_uuid(self):
        existing_eio = EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=self.informatieobjecttype
        )

        import_file_path = Path("import-test-files/foo.txt")

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        row = DocumentRowFactory(
            uuid=str(existing_eio.uuid),
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

    def test_unknown_zaak_uuid(self):
        import_file_path = Path("import-test-files/foo.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype,
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

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())

    def test_non_existent_file(self):
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())

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
            informatieobjecttype=self.informatieobjecttype,
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

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        self.assertFalse(imported_path.exists())

    @patch("openzaak.components.documenten.tasks.shutil.copy2")
    def test_unable_to_copy_file(self, patched_copy):
        patched_copy.side_effect = FileNotFoundError

        import_file_path = Path("import-test-files/foo.txt")

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=self.informatieobjecttype,
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

    def test_invalid_host_header(self):
        import_file_path = Path("import-test-files/foo.txt")
        import_file_content = "minimum fields"

        default_imported_file_path = get_default_path(
            EnkelvoudigInformatieObject.inhoud.field
        )

        imported_path = Path(default_imported_file_path) / import_file_path.name

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            import_file_content=import_file_content,
            informatieobjecttype=self.informatieobjecttype,
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
