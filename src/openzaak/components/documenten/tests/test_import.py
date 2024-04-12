from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, tag

from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.constants import Statussen
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.zaken.tests.factories import ZaakFactory


@tag("documenten-import")
class ImportDocumentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.test_path = Path(__file__).parent.resolve()

    def _setup_files(self, filenames):
        for filename in filenames:
            path = Path(f"/tmp/{filename}")
            path.touch()

            self.addCleanup(path.unlink, missing_ok=False)

    # TODO: assert file content
    # TODO: test that `bestandsnaam` is working properly whenever specified
    def test_simple_import(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        self._setup_files(("foobar.txt", "foobar.pdf", "foobar.docx"))

        zaak = ZaakFactory.create(uuid="d8ebc179-6de7-4400-a0bb-6f9e336d692e")

        import_file = self.test_path / "import_files" / "import.csv"

        call_command("import_documents", import_file=import_file)

        informatie_objects = EnkelvoudigInformatieObject.objects.all()
        zaak_informatie_object = zaak.zaakinformatieobject_set.get()

        self.assertEqual(informatie_objects.count(), 3)

        informatie_object = informatie_objects.first()

        self.assertEqual(informatie_object.bronorganisatie, "111222333")
        self.assertEqual(informatie_object.creatiedatum, date(2019, 8, 24))
        self.assertEqual(informatie_object.titel, "document XYZ")
        self.assertEqual(informatie_object.auteur, "organisatie-123")
        self.assertEqual(informatie_object.taal, "dut")
        self.assertEqual(informatie_object.informatieobjecttype, informatieobjecttype)

        # optional fields
        self.assertFalse(zaak_informatie_object.informatieobject == informatie_object)
        self.assertTrue(informatie_object.identificatie)
        self.assertEqual(informatie_object.vertrouwelijkheidaanduiding, "")
        self.assertEqual(informatie_object.status, "")
        self.assertEqual(informatie_object.formaat, "")
        self.assertEqual(informatie_object.bestandsnaam, "")
        self.assertEqual(informatie_object.beschrijving, "")
        self.assertEqual(informatie_object.verschijningsvorm, "")

        informatie_object = informatie_objects[1]

        self.assertEqual(informatie_object.bronorganisatie, "111222333")
        self.assertEqual(informatie_object.creatiedatum, date(2019, 8, 24))
        self.assertEqual(informatie_object.titel, "document YZX")
        self.assertEqual(informatie_object.auteur, "organisatie-123")
        self.assertEqual(informatie_object.taal, "eng")
        self.assertEqual(informatie_object.informatieobjecttype, informatieobjecttype)

        # optional fields
        self.assertFalse(zaak_informatie_object.informatieobject == informatie_object)
        self.assertTrue(informatie_object.identificatie)
        self.assertEqual(informatie_object.vertrouwelijkheidaanduiding, "")
        self.assertEqual(informatie_object.status, "")
        self.assertEqual(informatie_object.formaat, "")
        self.assertEqual(informatie_object.bestandsnaam, "")
        self.assertEqual(informatie_object.beschrijving, "")
        self.assertEqual(informatie_object.verschijningsvorm, "")

        informatie_object = informatie_objects.last()

        self.assertEqual(informatie_object.bronorganisatie, "111222333")
        self.assertEqual(informatie_object.creatiedatum, date(2019, 8, 24))
        self.assertEqual(informatie_object.titel, "document ZXY")
        self.assertEqual(informatie_object.auteur, "organisatie-123")
        self.assertEqual(informatie_object.taal, "dut")
        self.assertEqual(informatie_object.informatieobjecttype, informatieobjecttype)

        # optional fields
        self.assertFalse(zaak_informatie_object.informatieobject == informatie_object)
        self.assertEqual(informatie_object.identificatie, "identificatie-123")
        self.assertEqual(
            informatie_object.vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.intern,
        )
        self.assertEqual(informatie_object.status, Statussen.definitief)
        self.assertEqual(informatie_object.formaat, "application/pdf")
        self.assertEqual(informatie_object.bestandsnaam, "foobar.doc")
        self.assertEqual(informatie_object.beschrijving, "zeer mooi bestand")
        self.assertEqual(informatie_object.verschijningsvorm, "verschijningsvorm")

    # TODO: update this test so that the uniquness error occures in a batch
    # later on
    def test_identificatie_uniqueness(self):
        InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        self._setup_files(("foobar.txt", "foobar.pdf"))

        import_file = (
            self.test_path / "import_files" / "import_identificatie_uniqueness.csv"
        )

        with self.assertRaises(CommandError) as context_manager:
            call_command("import_documents", import_file=import_file)

        exception = context_manager.exception

        self.assertIn("identificatie-niet-uniek", str(exception))

    def test_incorrect_metadata(self):
        raise NotImplementedError

    def test_unknown_file_path(self):
        InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        import_file = self.test_path / "import_files" / "import_unknown_path.csv"

        with self.assertRaises(CommandError) as context_manager:
            call_command("import_documents", import_file=import_file)

        exception = context_manager.exception

        self.assertIn("pad-bestaat-niet", str(exception))

    def test_no_file_path(self):
        InformatieObjectTypeFactory.create(
            uuid="2eefe81d-8638-4306-b079-74e4e41f557b", concept=False
        )

        import_file = self.test_path / "import_files" / "import_no_path.csv"

        with self.assertRaises(CommandError) as context_manager:
            call_command("import_documents", import_file=import_file)

        exception = context_manager.exception

        self.assertIn("required", str(exception))

    def test_no_database_connection(self):
        raise NotImplementedError
