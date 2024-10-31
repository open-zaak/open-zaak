# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from io import BytesIO

from django.core.files import File

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from zgw_consumers.constants import APITypes

from openzaak.tests.utils import TestMigrations

from ..constants import ObjectInformatieObjectTypes


class MigrateCompositeUrlsForwardTest(TestMigrations):
    migrate_from = "0018_auto_20220906_1531"
    migrate_to = "0019_fill_documenten_service_urls"
    app = "documenten"

    def setUpBeforeMigration(self, apps):
        Service = apps.get_model("zgw_consumers", "Service")
        EnkelvoudigInformatieObjectCanonical = apps.get_model(
            "documenten", "EnkelvoudigInformatieObjectCanonical"
        )
        EnkelvoudigInformatieObject = apps.get_model(
            "documenten", "EnkelvoudigInformatieObject"
        )
        ObjectInformatieObject = apps.get_model("documenten", "ObjectInformatieObject")

        self.ztc_known = Service.objects.create(
            label="external Catalogi",
            slug="external-catalogi",
            api_type=APITypes.ztc,
            api_root="https://externe.catalogus.nl/api/v1/",
        )
        self.zrc_known = Service.objects.create(
            label="external Zaken",
            slug="external-zaken",
            api_type=APITypes.zrc,
            api_root="https://externe.zaken.nl/api/v1/",
        )

        io_canonical_known = EnkelvoudigInformatieObjectCanonical.objects.create()
        self.io_known = EnkelvoudigInformatieObject.objects.create(
            canonical=io_canonical_known,
            _informatieobjecttype_url=(
                f"{self.ztc_known.api_root}informatieobjecttypen/56750100-c537-45cb-a1d8-f39c2385a868"
            ),
            identificatie="known",
            bronorganisatie="517439943",
            creatiedatum="2020-01-01",
            titel="some document",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            auteur="John Smith",
            taal="nld",
            inhoud=File(BytesIO(b"some content"), name="filename.bin"),
        )
        self.oio_known = ObjectInformatieObject.objects.create(
            informatieobject=io_canonical_known,
            object_type=ObjectInformatieObjectTypes.zaak,
            _object_url=f"{self.zrc_known.api_root}zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )

        io_canonical_unknown = EnkelvoudigInformatieObjectCanonical.objects.create()
        self.io_unknown = EnkelvoudigInformatieObject.objects.create(
            canonical=io_canonical_unknown,
            _informatieobjecttype_url=(
                "https://andere.catalogus.nl/api/v1/informatieobjecttypen/56750100-c537-45cb-a1d8-f39c2385a868"
            ),
            identificatie="unknown",
            bronorganisatie="517439943",
            creatiedatum="2020-01-01",
            titel="some document",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            auteur="John Smith",
            taal="nld",
            inhoud=File(BytesIO(b"some content"), name="filename.bin"),
        )
        self.oio_unknown = ObjectInformatieObject.objects.create(
            informatieobject=io_canonical_unknown,
            object_type=ObjectInformatieObjectTypes.zaak,
            _object_url="https://andere.zaken.nl/api/v1/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )

    def test_composite_urls_filled(self):
        # 1. known service -> composite url fields are filled
        self.io_known.refresh_from_db()
        self.oio_known.refresh_from_db()

        self.assertEqual(
            self.io_known._informatieobjecttype_base_url.id, self.ztc_known.id
        )
        self.assertEqual(
            self.io_known._informatieobjecttype_relative_url,
            "informatieobjecttypen/56750100-c537-45cb-a1d8-f39c2385a868",
        )
        self.assertEqual(self.oio_known._object_base_url.pk, self.zrc_known.pk)
        self.assertEqual(
            self.oio_known._object_relative_url,
            "zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )

        # 2. unknown service -> composite url fields are filled and services are created
        Service = self.apps.get_model("zgw_consumers", "Service")
        self.assertTrue(
            Service.objects.filter(
                api_root="https://andere.catalogus.nl/api/v1/"
            ).exists()
        )
        self.assertTrue(
            Service.objects.filter(api_root="https://andere.zaken.nl/api/v1/").exists()
        )

        ztc_new = Service.objects.get(api_root="https://andere.catalogus.nl/api/v1/")
        zrc_new = Service.objects.get(api_root="https://andere.zaken.nl/api/v1/")
        for service in [ztc_new, zrc_new]:
            self.assertEqual(service.label, "FIXME")
            self.assertEqual(service.api_type, APITypes.orc)

        self.io_unknown.refresh_from_db()
        self.oio_unknown.refresh_from_db()

        self.assertEqual(
            self.io_known._informatieobjecttype_base_url.id, self.ztc_known.id
        )
        self.assertEqual(
            self.io_known._informatieobjecttype_relative_url,
            "informatieobjecttypen/56750100-c537-45cb-a1d8-f39c2385a868",
        )
        self.assertEqual(self.oio_known._object_base_url.pk, self.zrc_known.pk)
        self.assertEqual(
            self.oio_known._object_relative_url,
            "zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
