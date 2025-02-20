# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.contrib.sites.models import Site
from django.core.cache import caches
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings, tag

import requests_cache
import requests_mock

from openzaak.selectielijst.tests import mock_resource_get, mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import patch_resource_validator

from ...models import (
    BesluitType,
    Catalogus,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)

PATH = Path(__file__).parent.resolve()


class ImportExportMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def setUp(self):
        super().setUp()

        Site.objects.clear_cache()
        caches["import_requests"].clear()

        self.filepath = PATH / f"export_test{uuid4()}.zip"

        def rmfile():
            if not self.filepath.exists():
                return
            self.filepath.unlink()

        self.addCleanup(rmfile)


class ExportCatalogiTests(ImportExportMixin, TestCase):
    def test_export_catalogus(self):
        catalogus = CatalogusFactory.create()

        call_command(
            "export",
            archive_name=self.filepath,
            resource=["Catalogus"],
            ids=[[catalogus.id]],
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
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        resources = [
            "Catalogus",
            "ZaakType",
            "StatusType",
            "RolType",
            "ResultaatType",
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
            [resultaattype.id],
            [eigenschap.id],
            [informatieobjecttype.id],
            [besluittype.id],
            [ziot.id],
        ]
        call_command("export", archive_name=self.filepath, resource=resources, ids=ids)

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertIn("Catalogus.json", f.namelist())
            self.assertIn("ZaakType.json", f.namelist())
            self.assertIn("StatusType.json", f.namelist())
            self.assertIn("RolType.json", f.namelist())
            self.assertIn("ResultaatType.json", f.namelist())
            self.assertIn("Eigenschap.json", f.namelist())
            self.assertIn("InformatieObjectType.json", f.namelist())
            self.assertIn("BesluitType.json", f.namelist())
            self.assertIn("ZaakTypeInformatieObjectType.json", f.namelist())

    @override_settings(ALLOWED_HOSTS=["somedifferenthost.com"])
    def test_export_catalogus_different_hostname(self):
        site = Site.objects.get_current()
        site.domain = "somedifferenthost.com"
        site.save()

        catalogus = CatalogusFactory.create(
            rsin="000000000",
            domein="TEST",
            contactpersoon_beheer_naam="bla",
            contactpersoon_beheer_telefoonnummer="0612345678",
            contactpersoon_beheer_emailadres="test@test.nl",
        )

        call_command(
            "export",
            archive_name=self.filepath,
            resource=["Catalogus"],
            ids=[[catalogus.id]],
        )

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertEqual(f.namelist(), ["Catalogus.json"])

    @override_settings(
        ALLOWED_HOSTS=["openzaak.example.com", "testserver"],
        OPENZAAK_DOMAIN="openzaak.example.com:8443",
        IS_HTTPS=True,
    )
    def test_export_respects_openzaak_domain_setting(self):
        catalogus = CatalogusFactory.create(
            rsin="000000000",
            domein="TEST",
            contactpersoon_beheer_naam="bla",
            contactpersoon_beheer_telefoonnummer="0612345678",
            contactpersoon_beheer_emailadres="test@test.nl",
        )

        call_command(
            "export",
            archive_name=self.filepath,
            resource=["Catalogus"],
            ids=[[catalogus.id]],
        )

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertEqual(f.namelist(), ["Catalogus.json"])
            data = json.loads(f.read("Catalogus.json"))[0]

        self.assertTrue(data["url"].startswith("https://openzaak.example.com:8443/"))


@tag("catalogi-import")
class ImportCatalogiTests(SelectieLijstMixin, ImportExportMixin, TestCase):
    def test_import_catalogus(self):
        catalogus = CatalogusFactory.create(rsin="000000000")
        call_command(
            "export",
            archive_name=self.filepath,
            resource=["Catalogus"],
            ids=[[catalogus.id]],
        )

        catalogus.delete()
        call_command("import", import_file=self.filepath, generate_new_uuids=True)

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
            "export",
            archive_name=self.filepath,
            resource=["Catalogus"],
            ids=[[catalogus.id]],
        )

        self.assertRaises(
            CommandError,
            call_command,
            "import",
            import_file=self.filepath,
            generate_new_uuids=True,
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @requests_mock.Mocker()
    @patch_resource_validator
    def test_import_catalogus_with_relations(self, m, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
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

        resultaattypeomschrijving = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )
        selectielijstklasse = (
            f"{self.base}resultaten/d92e5a77-c523-4273-b8e0-c912115ef156"
        )
        mock_selectielijst_oas_get(m)
        mock_resource_get(m, "procestypen", zaaktype.selectielijst_procestype)
        mock_resource_get(m, "resultaattypeomschrijvingen", resultaattypeomschrijving)
        mock_resource_get(m, "resultaten", selectielijstklasse)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            omschrijving_generiek="bla",
            brondatum_archiefprocedure_afleidingswijze="afgehandeld",
            resultaattypeomschrijving=resultaattypeomschrijving,
            selectielijstklasse=selectielijstklasse,
        )
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        resources = [
            "Catalogus",
            "ZaakType",
            "StatusType",
            "RolType",
            "ResultaatType",
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
            [resultaattype.id],
            [eigenschap.id],
            [informatieobjecttype.id],
            [besluittype.id],
            [ziot.id],
        ]
        call_command("export", archive_name=self.filepath, resource=resources, ids=ids)

        catalogus.delete()

        call_command("import", import_file=self.filepath, generate_new_uuids=True)

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
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
        self.assertEqual(resultaattype.zaaktype, zaaktype)
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
        call_command("export", archive_name=self.filepath, resource=resources, ids=ids)

        catalogus.delete()
        call_command("import", import_file=self.filepath, generate_new_uuids=True)

        imported_catalogus = Catalogus.objects.get()
        zaaktypen = ZaakType.objects.order_by("zaaktype_omschrijving")
        self.assertEqual(zaaktypen.count(), 2)

        zaaktype1 = zaaktypen[0]
        zaaktype2 = zaaktypen[1]

        self.assertEqual(zaaktype1.catalogus, imported_catalogus)
        self.assertEqual(zaaktype1.zaaktype_omschrijving, "test1")

        self.assertEqual(zaaktype2.catalogus, imported_catalogus)
        self.assertEqual(zaaktype2.zaaktype_omschrijving, "test2")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @requests_mock.Mocker()
    @patch_resource_validator
    def test_import_request_caching(self, m, *mocks):
        """
        Assert that when running imports, external requests are cached to improve import performance
        """
        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )

        resultaattypeomschrijving = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )
        mock_resource_get(m, "resultaattypeomschrijvingen", resultaattypeomschrijving)
        selectielijstklasse = (
            f"{self.base}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        m.get(
            selectielijstklasse,
            json={
                "url": selectielijstklasse,
                "procesType": zaaktype.selectielijst_procestype,
                "nummer": 1,
                "naam": "bla",
                "herkomst": "adsad",
                "waardering": "blijvend_bewaren",
                "procestermijn": "P5Y",
            },
        )

        # Create multiple resultaattypen with same `resultaattypeomschrijving`
        resultaattypen = ResultaatTypeFactory.create_batch(
            10,
            zaaktype=zaaktype,
            brondatum_archiefprocedure_afleidingswijze="ander_datumkenmerk",
            brondatum_archiefprocedure_datumkenmerk="datum",
            brondatum_archiefprocedure_registratie="bla",
            brondatum_archiefprocedure_objecttype="besluit",
            resultaattypeomschrijving=resultaattypeomschrijving,
            selectielijstklasse=selectielijstklasse,
        )

        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        resources = [
            "Catalogus",
            "ZaakType",
            "ResultaatType",
        ]
        ids = [
            [catalogus.id],
            [zaaktype.id],
            [resultaattype.id for resultaattype in resultaattypen],
        ]
        call_command("export", archive_name=self.filepath, resource=resources, ids=ids)

        catalogus.delete()

        m.reset()

        call_command("import", import_file=self.filepath, generate_new_uuids=True)

        # Only two requests to retrieve the `selectielijstklasse` and
        # `resultaattypeomschrijving`, due to caching
        self.assertEqual(
            len(m.request_history), 2, [req.url for req in m.request_history]
        )
        [
            selectielijstklasse_request,
            resultaattypeomschrijving_request,
        ] = m.request_history

        self.assertEqual(selectielijstklasse_request.method, "GET")
        self.assertEqual(selectielijstklasse_request.url, selectielijstklasse)

        self.assertEqual(resultaattypeomschrijving_request.method, "GET")
        self.assertEqual(
            resultaattypeomschrijving_request.url, resultaattypeomschrijving
        )

        imported_catalogus = Catalogus.objects.get()
        zaaktype = ZaakType.objects.get()

        self.assertEqual(zaaktype.catalogus, imported_catalogus)
        self.assertEqual(ResultaatType.objects.count(), 10)
        self.assertEqual(ResultaatType.objects.filter(zaaktype=zaaktype).count(), 10)

        # Run another import, the cache should be reset between imports
        imported_catalogus.delete()

        m.reset()

        call_command("import", import_file=self.filepath, generate_new_uuids=True)

        # Only two requests to retrieve the `selectielijstklasse` and
        # `resultaattypeomschrijving`, due to caching
        self.assertEqual(
            len(m.request_history), 2, [req.url for req in m.request_history]
        )
        [
            selectielijstklasse_request,
            resultaattypeomschrijving_request,
        ] = m.request_history

        self.assertEqual(resultaattypeomschrijving_request.method, "GET")
        self.assertEqual(
            resultaattypeomschrijving_request.url,
            resultaattypeomschrijving,
        )

        self.assertEqual(resultaattypeomschrijving_request.method, "GET")
        self.assertEqual(
            resultaattypeomschrijving_request.url, resultaattypeomschrijving
        )

    @patch(
        "openzaak.utils.cache.uninstall_cache",
        side_effect=requests_cache.uninstall_cache,
    )
    def test_import_failure_uninstall_cache(self, uninstall_cache_mock):
        """
        Assert that when running imports, the requests cache is properly uninstalled if errors occur
        """

        with self.assertRaises(zipfile.BadZipFile):
            call_command("import", import_file_content=b"bad-data")

        # Cache should be uninstalled despite errors during import
        self.assertTrue(uninstall_cache_mock.called)
