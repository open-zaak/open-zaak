import json
import os
import zipfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ...models import (
    BesluitType,
    Catalogus,
    Eigenschap,
    InformatieObjectType,
    RolType,
    StatusType,
    ZaakTypeInformatieObjectType,
    ZaakType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
    ZaakTypeFactory,
)

PATH = os.path.abspath(os.path.dirname(__file__))


class ExportCatalogiTests(TestCase):
    def setUp(self):
        self.filepath = os.path.join(PATH, "export_test.zip")

    def test_export_catalogus(self):
        catalogus = CatalogusFactory.create()

        call_command(
            "export", self.filepath, resource=["Catalogus"], ids=[[catalogus.id]]
        )

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertEqual(f.namelist(), ["Catalogus.json"])

            data = json.loads(f.read("Catalogus.json"))[0]
            self.assertEqual(data["domein"], catalogus.domein)
            self.assertEqual(data["rsin"], catalogus.rsin)
            self.assertEqual(
                data["contactpersoon_beheer_naam"], catalogus.contactpersoon_beheer_naam
            )
            self.assertEqual(
                data["contactpersoon_beheer_telefoonnummer"],
                catalogus.contactpersoon_beheer_telefoonnummer,
            )
            self.assertEqual(
                data["contactpersoon_beheer_emailadres"],
                catalogus.contactpersoon_beheer_emailadres,
            )

    def test_export_catalogus_with_relations(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        resources = [
            "Catalogus",
            "ZaakType",
            "StatusType",
            "RolType",
            "Eigenschap",
            "InformatieObjectType",
            "BesluitType",
            "ZaakTypeInformatieObjectType",
        ]
        ids = [
            [catalogus.id],
            [zaaktype.id],
            [statustype.id],
            [roltype.id],
            [eigenschap.id],
            [informatieobjecttype.id],
            [besluittype.id],
            [ziot.id],
        ]
        call_command("export", self.filepath, resource=resources, ids=ids)

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertIn("Catalogus.json", f.namelist())
            self.assertIn("ZaakType.json", f.namelist())
            self.assertIn("StatusType.json", f.namelist())
            self.assertIn("RolType.json", f.namelist())
            self.assertIn("Eigenschap.json", f.namelist())
            self.assertIn("InformatieObjectType.json", f.namelist())
            self.assertIn("BesluitType.json", f.namelist())
            self.assertIn("ZaakTypeInformatieObjectType.json", f.namelist())

    def tearDown(self):
        os.remove(self.filepath)


class ImportCatalogiTests(TestCase):
    def setUp(self):
        self.filepath = os.path.join(PATH, "export_test.zip")

    def test_import_catalogus(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        call_command(
            "export", self.filepath, resource=["Catalogus"], ids=[[catalogus.id]]
        )

        catalogus.delete()
        call_command("import", self.filepath)

        imported_catalogus = Catalogus.objects.get()
        self.assertEqual(imported_catalogus.domein, catalogus.domein)
        self.assertEqual(imported_catalogus.rsin, catalogus.rsin)
        self.assertEqual(
            imported_catalogus.contactpersoon_beheer_naam,
            catalogus.contactpersoon_beheer_naam,
        )
        self.assertEqual(
            imported_catalogus.contactpersoon_beheer_telefoonnummer,
            catalogus.contactpersoon_beheer_telefoonnummer,
        )
        self.assertEqual(
            imported_catalogus.contactpersoon_beheer_emailadres,
            catalogus.contactpersoon_beheer_emailadres,
        )

        self.assertNotEqual(imported_catalogus.uuid, catalogus.uuid)

    def test_import_catalogus_fail_validation(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        call_command(
            "export", self.filepath, resource=["Catalogus"], ids=[[catalogus.id]]
        )

        self.assertRaises(CommandError, call_command, "import", self.filepath)

    def test_import_catalogus_with_relations(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        resources = [
            "Catalogus",
            "ZaakType",
            "StatusType",
            "RolType",
            "Eigenschap",
            "InformatieObjectType",
            "BesluitType",
            "ZaakTypeInformatieObjectType",
        ]
        ids = [
            [catalogus.id],
            [zaaktype.id],
            [statustype.id],
            [roltype.id],
            [eigenschap.id],
            [informatieobjecttype.id],
            [besluittype.id],
            [ziot.id],
        ]
        call_command("export", self.filepath, resource=resources, ids=ids)

        catalogus.delete()
        call_command("import", self.filepath)

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_import_catalogus_multiple_zaaktypes(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype1 = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="test1",
        )
        zaaktype2 = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="test2",
        )

        resources = [
            "Catalogus",
            "ZaakType",
        ]
        ids = [
            [catalogus.id],
            [zaaktype1.id, zaaktype2.id],
        ]
        call_command("export", self.filepath, resource=resources, ids=ids)

        catalogus.delete()
        call_command("import", self.filepath)

        imported_catalogus = Catalogus.objects.get()
        zaaktypen = ZaakType.objects.all()
        self.assertEqual(zaaktypen.count(), 2)

        zaaktype1 = zaaktypen[0]
        zaaktype2 = zaaktypen[1]

        self.assertEqual(zaaktype1.catalogus, imported_catalogus)
        self.assertEqual(zaaktype1.zaaktype_omschrijving, "test1")

        self.assertEqual(zaaktype2.catalogus, imported_catalogus)
        self.assertEqual(zaaktype2.zaaktype_omschrijving, "test2")

    def tearDown(self):
        os.remove(self.filepath)
