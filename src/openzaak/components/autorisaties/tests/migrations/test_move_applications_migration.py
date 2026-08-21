# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from datetime import date, timedelta

from openzaak.tests.utils import TestMigrations
from openzaak.utils.urls import reverse


class TestMoveApplicationsMigrations(TestMigrations):
    migrate_from = "0015_applicatie_alter_catalogusautorisatie_applicatie_and_more"
    migrate_to = "0016_move_applications"
    app = "autorisaties"
    execute_in_setup = False

    def setUpBeforeMigration(self, apps):
        self.ApplicatieOld = apps.get_model("authorizations", "Applicatie")
        self.AutorisatieOld = apps.get_model("authorizations", "Autorisatie")

        self.ApplicatieNew = apps.get_model("autorisaties", "Applicatie")
        self.AutorisatieNew = apps.get_model("autorisaties", "Autorisatie")

        self.CatalogusAutorisatie = apps.get_model(
            "autorisaties", "CatalogusAutorisatie"
        )
        self.ZaakType = apps.get_model("catalogi", "ZaakType")
        self.BesluitType = apps.get_model("catalogi", "BesluitType")
        self.InformatieObjectType = apps.get_model("catalogi", "InformatieObjectType")
        self.Catalogus = apps.get_model("catalogi", "Catalogus")

        self.ApplicatieOld.objects.create(
            uuid="ea55d56b-1149-4148-a9cf-3208375765d7",
            client_ids=["a", "b", "c"],
            label="superuser",
            heeft_alle_autorisaties=True,
        )

        self.catalogus = self.Catalogus.objects.create()

        self.besluittype = self.BesluitType.objects.create(
            catalogus=self.catalogus,
            datum_begin_geldigheid=date(2026, 1, 1),
            publicatie_indicatie=False,
        )

        self.zaaktype = self.ZaakType.objects.create(
            versiedatum=date(2026, 1, 1),
            datum_begin_geldigheid=date(2026, 1, 1),
            doorlooptijd_behandeling=timedelta(days=10),
            opschorting_en_aanhouding_mogelijk=False,
            verlenging_mogelijk=False,
            publicatie_indicatie=False,
            catalogus=self.catalogus,
        )
        self.informatieobjecttype = self.InformatieObjectType.objects.create(
            datum_begin_geldigheid=date(2026, 1, 1),
            catalogus=self.catalogus,
        )

        self.app = self.ApplicatieOld.objects.create(
            uuid="5b5486fc-6e29-4861-a39f-b478762758ad",
            client_ids=["a", "b", "c"],
            label="admin",
            heeft_alle_autorisaties=False,
        )

        self.CatalogusAutorisatie.objects.create(
            applicatie=self.app,
            catalogus=self.catalogus,
            component="zrc",
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        # internal besluittype
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="brc",
            scopes=["besluiten.lezen"],
            besluittype=f"http://testserver{reverse(self.besluittype)}",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        # internal zaaktype
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="zrc",
            scopes=["zaken.lezen"],
            zaaktype=f"http://testserver{reverse(self.zaaktype)}",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        # internal iot
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="drc",
            scopes=["documenten.lezen"],
            informatieobjecttype=f"http://testserver{reverse(self.informatieobjecttype)}",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="nrc",
            scopes=["notificaties.consumeren"],
        )

        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="ac",
            scopes=["autorisatie.lezen"],
        )

        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="ztc",
            scopes=["catalogi.lezen"],
        )



    def test_move(self):
        self.execute()
        self.assertEqual(self.ApplicatieOld.objects.count(), 0)
        self.assertEqual(self.AutorisatieOld.objects.count(), 0)
        self.assertEqual(self.CatalogusAutorisatie.objects.count(), 1)
        self.assertEqual(self.ApplicatieNew.objects.count(), 2)
        self.assertEqual(self.AutorisatieNew.objects.count(), 6)

        superuser_app = self.ApplicatieNew.objects.get(
            uuid="ea55d56b-1149-4148-a9cf-3208375765d7"
        )
        self.assertEqual(superuser_app.label, "superuser")
        self.assertEqual(superuser_app.heeft_alle_autorisaties, True)
        self.assertEqual(superuser_app.client_ids, ["a", "b", "c"])
        self.assertEqual(superuser_app.autorisaties.count(), 0)

        app = self.ApplicatieNew.objects.get(
            uuid="5b5486fc-6e29-4861-a39f-b478762758ad"
        )
        self.assertEqual(app.label, "admin")
        self.assertEqual(app.heeft_alle_autorisaties, False)
        self.assertEqual(app.client_ids, ["a", "b", "c"])
        self.assertEqual(app.autorisaties.count(), 6)

        cat_auth = self.CatalogusAutorisatie.objects.get()
        self.assertEqual(cat_auth.applicatie, None)
        self.assertEqual(cat_auth.new_applicatie, app)
        self.assertEqual(cat_auth.catalogus, self.catalogus)
        self.assertEqual(cat_auth.component, "zrc")
        self.assertEqual(cat_auth.scopes, ["zaken.lezen"])
        self.assertEqual(cat_auth.max_vertrouwelijkheidaanduiding, "openbaar")

        brc_auth = self.AutorisatieNew.objects.get(component="brc")
        self.assertEqual(brc_auth.applicatie, app)
        self.assertEqual(brc_auth.scopes, ["besluiten.lezen"])
        self.assertEqual(brc_auth.max_vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(brc_auth.besluittype, self.besluittype)
        self.assertEqual(brc_auth.zaaktype, None)
        self.assertEqual(brc_auth.informatieobjecttype, None)

        zrc_auth = self.AutorisatieNew.objects.get(component="zrc")
        self.assertEqual(zrc_auth.applicatie, app)
        self.assertEqual(zrc_auth.scopes, ["zaken.lezen"])
        self.assertEqual(zrc_auth.max_vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(zrc_auth.besluittype, None)
        self.assertEqual(zrc_auth.zaaktype, self.zaaktype)
        self.assertEqual(zrc_auth.informatieobjecttype, None)

        drc_auth = self.AutorisatieNew.objects.get(component="drc")
        self.assertEqual(drc_auth.applicatie, app)
        self.assertEqual(drc_auth.scopes, ["documenten.lezen"])
        self.assertEqual(drc_auth.max_vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(drc_auth.besluittype, None)
        self.assertEqual(drc_auth.zaaktype, None)
        self.assertEqual(drc_auth.informatieobjecttype, self.informatieobjecttype)

        nrc_auth = self.AutorisatieNew.objects.get(component="nrc")
        self.assertEqual(nrc_auth.applicatie, app)
        self.assertEqual(nrc_auth.scopes, ["notificaties.consumeren"])
        self.assertEqual(nrc_auth.besluittype, None)
        self.assertEqual(nrc_auth.zaaktype, None)
        self.assertEqual(nrc_auth.informatieobjecttype, None)

        ac_auth = self.AutorisatieNew.objects.get(component="ac")
        self.assertEqual(ac_auth.applicatie, app)
        self.assertEqual(ac_auth.scopes, ["autorisatie.lezen"])
        self.assertEqual(ac_auth.besluittype, None)
        self.assertEqual(ac_auth.zaaktype, None)
        self.assertEqual(ac_auth.informatieobjecttype, None)

        ztc_auth = self.AutorisatieNew.objects.get(component="ztc")
        self.assertEqual(ztc_auth.applicatie, app)
        self.assertEqual(ztc_auth.scopes, ["catalogi.lezen"])
        self.assertEqual(ztc_auth.besluittype, None)
        self.assertEqual(ztc_auth.zaaktype, None)
        self.assertEqual(ztc_auth.informatieobjecttype, None)

    def test_external_url(self):
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="brc",
            scopes=["besluiten.aanmaken"],
            besluittype="http://external/catalogi/api/v1/zaaktypen/ea55d56b-1149-4148-a9cf-3208375765d7",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        with self.assertRaisesMessage(ValueError, "http://external/catalogi/api/v1/zaaktypen/ea55d56b-1149-4148-a9cf-3208375765d7 is not a local URL"):
            self.execute()

    def test_invalid_internal_url(self):
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="brc",
            scopes=["besluiten.lezen"],
            besluittype="http://testserver/catalogi/api/v1/blabla/ea55d56b-1149-4148-a9cf-3208375765d7",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        with self.assertRaisesMessage(ValueError, "http://testserver/catalogi/api/v1/blabla/ea55d56b-1149-4148-a9cf-3208375765d7 is not a valid URL"):
            self.execute()

    def test_unexpected_resource(self):
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="brc",
            scopes=["besluiten.lezen"],
            besluittype=f"http://testserver{reverse(self.zaaktype)}",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        with self.assertRaisesMessage(ValueError, f"http://testserver{reverse(self.zaaktype)} is not a expected besluittypen resource"):
            self.execute()

    def test_non_existent_uuid(self):
        self.AutorisatieOld.objects.create(
            applicatie=self.app,
            component="brc",
            scopes=["besluiten.lezen"],
            besluittype="http://testserver/catalogi/api/v1/besluittypen/255c2111-774a-4c2a-bb77-34301101c09d",
            max_vertrouwelijkheidaanduiding="openbaar",
        )

        with self.assertRaisesMessage(ValueError,
                                      "http://testserver/catalogi/api/v1/besluittypen/255c2111-774a-4c2a-bb77-34301101c09d does not exist"):
            self.execute()
