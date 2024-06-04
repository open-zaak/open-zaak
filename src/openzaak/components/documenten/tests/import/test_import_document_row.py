# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings

from vng_api_common.fields import VertrouwelijkheidsAanduiding
from vng_api_common.utils import generate_unique_identification

from openzaak.components.catalogi.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)
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
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.import_data.tests.factories import get_informatieobjecttype_url
from openzaak.import_data.tests.utils import ImportTestFileMixin
from openzaak.utils.fields import get_default_path


@override_settings(IMPORT_DOCUMENTEN_BASE_DIR="/tmp/import")
class ImportDocumentRowTests(ImportTestFileMixin, TestCase):
    def test_minimum_fields(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            concept=False,
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

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
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

        eio = document_row.instance

        self.assertIs(type(eio), EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.informatieobjecttype, informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        with open(imported_path, "r") as file:
            self.assertEqual(file.read(), import_file_content)

    def test_all_fields(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        zaak = ZaakFactory()

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

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
            informatieobjecttype=informatieobjecttype_url,
            zaak_id=str(zaak.uuid),
            trefwoorden='"foo,bar"',
        )

        document_row = _import_document_row(row, 0, [], {str(zaak.uuid): zaak.pk})

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
            {"soort": OndertekeningSoorten.analoog, "datum": date(2024, 1, 1),},
        )

        self.assertEqual(
            eio.integriteit,
            {
                "algoritme": ChecksumAlgoritmes.crc_16,
                "datum": date(2024, 1, 1),
                "waarde": "foo",
            },
        )
        self.assertEqual(eio.informatieobjecttype, informatieobjecttype)
        self.assertEqual(eio.trefwoorden, ["foo", "bar"])

        with open(imported_path, "r") as file:
            self.assertEqual(file.read(), import_file_content)

    def test_upload_dir_does_not_exist(self):
        """
        Test that the files are correctly copied to the upload dir even tough it
        does not exist yet
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            concept=False,
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

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
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

        eio = document_row.instance

        self.assertIs(type(eio), EnkelvoudigInformatieObject)

        self.assertTrue(eio.uuid)
        self.assertTrue(eio.identificatie)
        self.assertEqual(eio.bronorganisatie, "706284513")
        self.assertEqual(eio.creatiedatum, date(2024, 1, 1))
        self.assertEqual(eio.titel, "Document XYZ")
        self.assertEqual(eio.auteur, "Auteur Y")
        self.assertEqual(eio.taal, "nld")
        self.assertEqual(eio.informatieobjecttype, informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "")

        with open(imported_path, "r") as file:
            self.assertEqual(file.read(), import_file_content)

    def test_lower_column_count(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row[:5], 0, [], {})

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("insufficient row count", document_row.comment)

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_validation_error(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="foobar",  # Incorrect date
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("creatiedatum", document_row.comment)

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_invalid_uuid(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)
        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            uuid="invalid-uuid",
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("not a valid UUID (version 4)", document_row.comment)

        default_file_path = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_existing_uuid(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        existing_eio = EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)
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
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [str(existing_eio.uuid)], {})

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("was already found", document_row.comment)
        self.assertIn("Not overwriting existing EIO", document_row.comment)

        file_path = Path(default_file_path) / import_file_path.name

        self.assertFalse(file_path.exists())

    def test_unknown_zaak_id(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            concept=False,
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

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
            informatieobjecttype=informatieobjecttype_url,
            zaak_id="b0f3681d-945a-4b30-afcb-12cad0a3eeaf",
        )

        document_row = _import_document_row(row, 0, [], {})

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
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

        import_file_path = Path("import-test-files/foo.txt")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            informatieobjecttype=informatieobjecttype_url,
            ignore_import_path=True,
        )

        document_row = _import_document_row(row, 0, [], {})

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
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

        import_file_path = Path("import-test-files/foobar/")

        row = DocumentRowFactory(
            bronorganisatie="706284513",
            creatiedatum="2024-01-01",
            titel="Document XYZ",
            auteur="Auteur Y",
            taal="nld",
            bestandspad=str(import_file_path),
            is_dir=True,
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

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

        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            concept=False,
        )

        informatieobjecttype_url = get_informatieobjecttype_url(informatieobjecttype)

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
            informatieobjecttype=informatieobjecttype_url,
        )

        document_row = _import_document_row(row, 0, [], {})

        eio = document_row.instance

        self.assertIsNone(eio)

        self.assertTrue(document_row.processed)
        self.assertFalse(document_row.succeeded)

        self.assertIn("Unable to copy file for row", document_row.comment)

        self.assertFalse(imported_path.exists())
