# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.test import tag

from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding

from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
)
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.tests.utils import TestMigrations


@tag("gh-1661")
class MigrateAutorisatieSpecsToCatalogusAutorisatiesTest(TestMigrations):
    migrate_from = "0010_catalogusautorisatie"
    migrate_to = "0011_autorisatiespec_to_catalogusautorisatie"
    app = "autorisaties"

    def setUpBeforeMigration(self, apps):
        Applicatie = apps.get_model("authorizations", "Applicatie")
        Autorisatie = apps.get_model("authorizations", "Autorisatie")
        AutorisatieSpec = apps.get_model("autorisaties", "AutorisatieSpec")
        Catalogus = apps.get_model("catalogi", "Catalogus")

        self.catalogus1 = Catalogus.objects.create(
            domein="AAAAA",
            naam="Some Catalogus",
            rsin="000000000",
        )
        self.catalogus2 = Catalogus.objects.create(
            domein="BBBBB",
            naam="Some Catalogus2",
            rsin="000000000",
        )
        self.applicatie = Applicatie.objects.create(
            label="Some applicatie",
            client_ids=["foo"],
        )
        AutorisatieSpec.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        AutorisatieSpec.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=[SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN, SCOPE_DOCUMENTEN_AANMAKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        # different scopes and vertrouwelijkheidaanduiding, scope should be added to scopes
        # above
        AutorisatieSpec.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=[SCOPE_DOCUMENTEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        AutorisatieSpec.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=[SCOPE_BESLUITEN_AANMAKEN, SCOPE_BESLUITEN_ALLES_VERWIJDEREN],
        )
        # Autorisaties added by the first spec, should be deleted after migration
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaaktype="http://zaaktypen.nl/1",
        )
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaaktype="http://zaaktypen.nl/2",
        )

        # Manual autorisatie with different scopes, should be left intact
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_CREATE],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaaktype="http://zaaktypen.nl/3",
        )

    def test_catalogus_autorisaties_created(self):
        Autorisatie = self.apps.get_model("authorizations", "Autorisatie")
        CatalogusAutorisatie = self.apps.get_model(
            "autorisaties", "CatalogusAutorisatie"
        )

        catalogus_autorisaties = CatalogusAutorisatie.objects.all()
        self.assertEqual(catalogus_autorisaties.count(), 6)

        zrc_autorisatie1, zrc_autorisatie2 = catalogus_autorisaties.filter(
            component=ComponentTypes.zrc
        )

        self.assertEqual(zrc_autorisatie1.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            zrc_autorisatie1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )
        self.assertEqual(
            zrc_autorisatie1.scopes,
            [str(SCOPE_ZAKEN_ALLES_LEZEN), str(SCOPE_ZAKEN_BIJWERKEN)],
        )
        self.assertEqual(zrc_autorisatie1.catalogus.naam, self.catalogus1.naam)
        self.assertEqual(zrc_autorisatie2.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            zrc_autorisatie2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )
        self.assertEqual(
            zrc_autorisatie2.scopes,
            [str(SCOPE_ZAKEN_ALLES_LEZEN), str(SCOPE_ZAKEN_BIJWERKEN)],
        )
        self.assertEqual(zrc_autorisatie2.catalogus.naam, self.catalogus2.naam)

        self.assertEqual(Autorisatie.objects.count(), 1)

        remaining_autorisatie = Autorisatie.objects.get()

        self.assertEqual(remaining_autorisatie.applicatie.label, self.applicatie.label)
        self.assertEqual(remaining_autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(remaining_autorisatie.scopes, [str(SCOPE_ZAKEN_CREATE)])
        self.assertEqual(
            remaining_autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )
        self.assertEqual(remaining_autorisatie.zaaktype, "http://zaaktypen.nl/3")

        drc_autorisatie1, drc_autorisatie2 = catalogus_autorisaties.filter(
            component=ComponentTypes.drc
        )

        self.assertEqual(drc_autorisatie1.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            drc_autorisatie1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(
            drc_autorisatie1.scopes,
            [
                str(SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN),
                str(SCOPE_DOCUMENTEN_AANMAKEN),
                str(SCOPE_DOCUMENTEN_BIJWERKEN),
            ],
        )
        self.assertEqual(drc_autorisatie1.catalogus.naam, self.catalogus1.naam)
        self.assertEqual(drc_autorisatie2.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            drc_autorisatie2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(
            drc_autorisatie2.scopes,
            [
                str(SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN),
                str(SCOPE_DOCUMENTEN_AANMAKEN),
                str(SCOPE_DOCUMENTEN_BIJWERKEN),
            ],
        )
        self.assertEqual(drc_autorisatie2.catalogus.naam, self.catalogus2.naam)

        brc_autorisatie1, brc_autorisatie2 = catalogus_autorisaties.filter(
            component=ComponentTypes.brc
        )

        self.assertEqual(brc_autorisatie1.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            brc_autorisatie1.scopes,
            [str(SCOPE_BESLUITEN_AANMAKEN), str(SCOPE_BESLUITEN_ALLES_VERWIJDEREN)],
        )
        self.assertEqual(brc_autorisatie1.catalogus.naam, self.catalogus1.naam)
        self.assertEqual(brc_autorisatie2.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            brc_autorisatie2.scopes,
            [str(SCOPE_BESLUITEN_AANMAKEN), str(SCOPE_BESLUITEN_ALLES_VERWIJDEREN)],
        )
        self.assertEqual(brc_autorisatie2.catalogus.naam, self.catalogus2.naam)


@tag("gh-1661")
class MigrateCatalogusAutorisatiesToAutorisatieSpecsTest(TestMigrations):
    migrate_from = "0013_alter_catalogusautorisatie_component"
    migrate_to = "0010_catalogusautorisatie"
    app = "autorisaties"

    def setUpBeforeMigration(self, apps):
        Applicatie = apps.get_model("authorizations", "Applicatie")
        CatalogusAutorisatie = apps.get_model("autorisaties", "CatalogusAutorisatie")
        Catalogus = apps.get_model("catalogi", "Catalogus")

        self.catalogus1 = Catalogus.objects.create(
            domein="AAAAA",
            naam="Some Catalogus",
            rsin="000000000",
        )
        self.catalogus2 = Catalogus.objects.create(
            domein="BBBBB",
            naam="Some Catalogus2",
            rsin="000000000",
        )
        self.applicatie = Applicatie.objects.create(
            label="Some applicatie",
            client_ids=["foo"],
        )
        CatalogusAutorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            catalogus_id=self.catalogus1.id,
        )
        CatalogusAutorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
            catalogus_id=self.catalogus2.id,
        )

    def test_autorisatiespecs_created(self):
        AutorisatieSpec = self.apps.get_model("autorisaties", "AutorisatieSpec")

        spec = AutorisatieSpec.objects.get()

        self.assertEqual(spec.applicatie.pk, self.applicatie.pk)
        self.assertEqual(
            spec.max_vertrouwelijkheidaanduiding, VertrouwelijkheidsAanduiding.openbaar
        )
        self.assertEqual(
            spec.scopes, [str(SCOPE_ZAKEN_ALLES_LEZEN), str(SCOPE_ZAKEN_BIJWERKEN)]
        )
        self.assertEqual(spec.component, ComponentTypes.zrc)


class RemoveOrphanedJwtSecretsTest(TestMigrations):
    migrate_from = "0013_alter_catalogusautorisatie_component"
    migrate_to = "0014_remove_orphaned_jwtsecrets"
    app = "autorisaties"

    def setUpBeforeMigration(self, apps):
        Applicatie = apps.get_model("authorizations", "Applicatie")
        JWTSecret = apps.get_model("vng_api_common", "JWTSecret")

        Applicatie.objects.create(label="test1", client_ids=["keep"])
        self.jwt_keep = JWTSecret.objects.create(identifier="keep", secret="secret1")
        JWTSecret.objects.create(identifier="to-remove", secret="secret2")

    def test_jwtsecrets_removed(self):
        JWTSecret = self.apps.get_model("vng_api_common", "JWTSecret")

        self.assertEqual(JWTSecret.objects.count(), 1)
        self.assertEqual(JWTSecret.objects.get().id, self.jwt_keep.id)
