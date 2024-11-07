# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from zgw_consumers.constants import APITypes

from openzaak.tests.utils import TestMigrations


class MigrateCompositeUrlsForwardTest(TestMigrations):
    migrate_from = "0007_auto_20220804_1522"
    migrate_to = "0008_fill_besluit_service_urls"
    app = "besluiten"

    def setUpBeforeMigration(self, apps):
        Service = apps.get_model("zgw_consumers", "Service")
        Besluit = apps.get_model("besluiten", "Besluit")
        BesluitInformatieObject = apps.get_model("besluiten", "BesluitInformatieObject")

        self.ztc_known = Service.objects.create(
            label="external Catalogi",
            slug="externe-catalogi",
            api_type=APITypes.ztc,
            api_root="https://externe.catalogus.nl/api/v1/",
        )
        self.zrc_known = Service.objects.create(
            label="external Zaken",
            slug="external-zaken",
            api_type=APITypes.zrc,
            api_root="https://externe.zaken.nl/api/v1/",
        )
        self.drc_known = Service.objects.create(
            label="external Documenten",
            slug="external-documenten",
            api_type=APITypes.drc,
            api_root="https://externe.documenten.nl/api/v1/",
        )
        self.besluit_known = Besluit.objects.create(
            identificatie="known",
            verantwoordelijke_organisatie="517439943",
            _besluittype_url=f"{self.ztc_known.api_root}besluittypen/56750100-c537-45cb-a1d8-f39c2385a868",
            _zaak_url=f"{self.zrc_known.api_root}zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            datum="2018-09-06",
            ingangsdatum="2018-10-01",
        )
        self.bio_known = BesluitInformatieObject.objects.create(
            besluit=self.besluit_known,
            _informatieobject_url=(
                f"{self.drc_known.api_root}informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e"
            ),
        )
        self.besluit_unknown = Besluit.objects.create(
            identificatie="unknown",
            verantwoordelijke_organisatie="517439943",
            _besluittype_url="https://andere.catalogus.nl/api/v1/besluittypen/56750100-c537-45cb-a1d8-f39c2385a868",
            _zaak_url="https://andere.zaken.nl/api/v1/zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            datum="2018-09-06",
            ingangsdatum="2018-10-01",
        )
        self.bio_unknown = BesluitInformatieObject.objects.create(
            besluit=self.besluit_known,
            _informatieobject_url=(
                "https://andere.documenten.nl/api/v1/informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e"
            ),
        )

    def test_composite_urls_filled(self):
        # 1. known service -> composite url fields are filled
        self.besluit_known.refresh_from_db()
        self.bio_known.refresh_from_db()

        self.assertEqual(self.besluit_known._besluittype_base_url.pk, self.ztc_known.pk)
        self.assertEqual(
            self.besluit_known._besluittype_relative_url,
            "besluittypen/56750100-c537-45cb-a1d8-f39c2385a868",
        )
        self.assertEqual(self.besluit_known._zaak_base_url.pk, self.zrc_known.pk)
        self.assertEqual(
            self.besluit_known._zaak_relative_url,
            "zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.bio_known._informatieobject_base_url.pk, self.drc_known.pk
        )
        self.assertEqual(
            self.bio_known._informatieobject_relative_url,
            "informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
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
        self.assertTrue(
            Service.objects.filter(
                api_root="https://andere.documenten.nl/api/v1/"
            ).exists()
        )

        ztc_new = Service.objects.get(api_root="https://andere.catalogus.nl/api/v1/")
        zrc_new = Service.objects.get(api_root="https://andere.zaken.nl/api/v1/")
        drc_new = Service.objects.get(api_root="https://andere.documenten.nl/api/v1/")
        for service in [ztc_new, zrc_new, drc_new]:
            self.assertEqual(service.label, "FIXME")
            self.assertEqual(service.api_type, APITypes.orc)

        self.besluit_unknown.refresh_from_db()
        self.bio_unknown.refresh_from_db()

        self.assertEqual(self.besluit_unknown._besluittype_base_url.pk, ztc_new.pk)
        self.assertEqual(
            self.besluit_unknown._besluittype_relative_url,
            "besluittypen/56750100-c537-45cb-a1d8-f39c2385a868",
        )
        self.assertEqual(self.besluit_unknown._zaak_base_url.pk, zrc_new.pk)
        self.assertEqual(
            self.besluit_unknown._zaak_relative_url,
            "zaken/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(self.bio_unknown._informatieobject_base_url.pk, drc_new.pk)
        self.assertEqual(
            self.bio_unknown._informatieobject_relative_url,
            "informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
        )
