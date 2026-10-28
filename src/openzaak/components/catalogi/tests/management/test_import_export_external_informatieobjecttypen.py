# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
"""
Import/export of relations to external informatieobjecttypen.
"""

import json
import uuid
import zipfile

from django.core.management import call_command
from django.test import TestCase, override_settings, tag

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.documenten.tests.utils import (
    get_informatieobjecttype_response,
)
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import mock_drc_oas_get

from ...models import (
    BesluitType,
    BesluitTypeInformatieObjectType,
    Catalogus,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from .test_import_export import ImportExportMixin

BASE = "https://external.documenten.nl/api/v1/"
CATALOGUS = f"{BASE}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
RESOURCES = [
    "Catalogus",
    "ZaakType",
    "InformatieObjectType",
    "BesluitType",
    "ZaakTypeInformatieObjectType",
]


@tag("catalogi-import", "external-urls")
@override_settings(SITE_DOMAIN="testserver", ALLOWED_HOSTS=["testserver"])
class ExternalInformatieObjectTypeImportExportTests(
    SelectieLijstMixin, ImportExportMixin, TestCase
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=BASE,
            label="external documenten",
            auth_type=AuthTypes.no_auth,
        )

    def _create_catalogus(self):
        self.external = f"{BASE}informatieobjecttypen/{uuid.uuid4()}"

        catalogus = CatalogusFactory.create(rsin="000000000")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        local = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar", zaaktypen=[]
        )
        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, informatieobjecttypen=[]
        )
        besluittype.zaaktypen.set([zaaktype])
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=local
        )
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=self.external
        )
        ziot_local = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=local,
            volgnummer=1,
            richting="inkomend",
        )
        ziot_external = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=self.external,
            volgnummer=2,
            richting="uitgaand",
        )
        Catalogus.objects.exclude(pk=catalogus.pk).delete()
        return catalogus, zaaktype, local, besluittype, [ziot_local, ziot_external]

    def _export(self, catalogus, zaaktype, local, besluittype, ziots):
        ids = [
            [catalogus.id],
            [zaaktype.id],
            [local.id],
            [besluittype.id],
            [ziot.id for ziot in ziots],
        ]
        call_command("export", archive_name=self.filepath, resource=RESOURCES, ids=ids)

    def test_export(self):
        self._export(*self._create_catalogus())

        with zipfile.ZipFile(self.filepath, "r") as f:
            besluittype = json.loads(f.read("BesluitType.json"))[0]
            ziots = json.loads(f.read("ZaakTypeInformatieObjectType.json"))

        self.assertEqual(len(besluittype["informatieobjecttypen"]), 2)
        self.assertIn(self.external, besluittype["informatieobjecttypen"])
        self.assertIn(self.external, [ziot["informatieobjecttype"] for ziot in ziots])

    def test_import(self):
        self._export(*self._create_catalogus())
        Catalogus.objects.all().delete()

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(
                self.external,
                json=get_informatieobjecttype_response(CATALOGUS, self.external),
            )
            call_command("import", import_file=self.filepath, generate_new_uuids=True)

        besluittype = BesluitType.objects.get()
        self.assertEqual(besluittype.informatieobjecttypen.count(), 1)
        relations = besluittype.besluittypeinformatieobjecttype_set.order_by("pk")
        self.assertEqual(relations.count(), 2)
        self.assertEqual(
            relations[0].informatieobjecttype, besluittype.informatieobjecttypen.get()
        )
        self.assertEqual(relations[1]._iotype_url, self.external)

        zaaktype = ZaakType.objects.get()
        ziots = zaaktype.zaaktypeinformatieobjecttype_set.order_by("volgnummer")
        self.assertEqual(ziots.count(), 2)
        self.assertEqual(
            ziots[0].informatieobjecttype, besluittype.informatieobjecttypen.get()
        )
        self.assertEqual(ziots[1]._iotype_url, self.external)

    def test_catalogus_admin_export_includes_external_relations(self):
        from django.contrib import admin

        catalogus, *_, ziots = self._create_catalogus()
        catalogus_admin = admin.site._registry[Catalogus]

        resources, ids = catalogus_admin.get_related_objects(catalogus)

        ziot_ids = ids[resources.index("ZaakTypeInformatieObjectType")]
        self.assertCountEqual(ziot_ids, [ziot.pk for ziot in ziots])
