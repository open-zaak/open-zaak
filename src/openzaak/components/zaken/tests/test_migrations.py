# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.utils import timezone

from vng_api_common.constants import (
    RelatieAarden,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from zgw_consumers.constants import APITypes

from openzaak.tests.utils import TestMigrations

from ..constants import AardZaakRelatie


class MigrateCompositeUrlsForwardTest(TestMigrations):
    migrate_from = "0010_auto_20220815_1742"
    migrate_to = "0011_fill_service_urls"
    app = "zaken"

    def setUpBeforeMigration(self, apps):
        Service = apps.get_model("zgw_consumers", "Service")
        Zaak = apps.get_model("zaken", "Zaak")
        RelevanteZaakRelatie = apps.get_model("zaken", "RelevanteZaakRelatie")
        Status = apps.get_model("zaken", "Status")
        Resultaat = apps.get_model("zaken", "Resultaat")
        Rol = apps.get_model("zaken", "Rol")
        ZaakEigenschap = apps.get_model("zaken", "ZaakEigenschap")
        ZaakInformatieObject = apps.get_model("zaken", "ZaakInformatieObject")
        ZaakBesluit = apps.get_model("zaken", "ZaakBesluit")

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
        self.drc_known = Service.objects.create(
            label="external Documenten",
            slug="external-documenten",
            api_type=APITypes.drc,
            api_root="https://externe.documenten.nl/api/v1/",
        )
        self.brc_known = Service.objects.create(
            label="external Besluiten",
            slug="external-besluiten",
            api_type=APITypes.brc,
            api_root="https://externe.besluiten.nl/api/v1/",
        )

        self.zaak_known = Zaak.objects.create(
            _zaaktype_url=f"{self.ztc_known.api_root}zaaktypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            identificatie="known",
            bronorganisatie="517439943",
            verantwoordelijke_organisatie="517439943",
            startdatum="2020-01-01",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.relevante_zaak_known = RelevanteZaakRelatie.objects.create(
            zaak=self.zaak_known,
            _relevant_zaak_url=f"{self.zrc_known.api_root}zaken/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
            aard_relatie=AardZaakRelatie.bijdrage,
        )
        self.status_known = Status.objects.create(
            zaak=self.zaak_known,
            _statustype_url=f"{self.ztc_known.api_root}statustypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            datum_status_gezet=timezone.now(),
        )
        self.resultaat_known = Resultaat.objects.create(
            zaak=self.zaak_known,
            _resultaattype_url=f"{self.ztc_known.api_root}resultaattypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.rol_known = Rol.objects.create(
            zaak=self.zaak_known,
            _roltype_url=f"{self.ztc_known.api_root}roltypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            betrokkene="https//personen.nl/1",
            betrokkene_type=RolTypes.medewerker,
            roltoelichting="known rol",
        )
        self.zaak_eigenschap_known = ZaakEigenschap.objects.create(
            zaak=self.zaak_known,
            _eigenschap_url=f"{self.ztc_known.api_root}eigenschappen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            _naam="known",
        )
        self.zio_known = ZaakInformatieObject.objects.create(
            zaak=self.zaak_known,
            _informatieobject_url=(
                f"{self.drc_known.api_root}informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e"
            ),
            aard_relatie=RelatieAarden.hoort_bij,
        )
        self.zaak_besluit_known = ZaakBesluit.objects.create(
            zaak=self.zaak_known,
            _besluit_url=f"{self.brc_known.api_root}besluiten/9b235f85-4f39-49df-ab6e-9c2d32123cf5",
        )

        self.zaak_unknown = Zaak.objects.create(
            _zaaktype_url="https://andere.catalogus.nl/api/v1/zaaktypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            identificatie="unknown",
            bronorganisatie="517439943",
            verantwoordelijke_organisatie="517439943",
            startdatum="2020-01-01",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.relevante_zaak_unknown = RelevanteZaakRelatie.objects.create(
            zaak=self.zaak_unknown,
            _relevant_zaak_url="https://andere.zaken.nl/api/v1/zaken/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
            aard_relatie=AardZaakRelatie.bijdrage,
        )
        self.status_unknown = Status.objects.create(
            zaak=self.zaak_unknown,
            _statustype_url="https://andere.catalogus.nl/api/v1/statustypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            datum_status_gezet=timezone.now(),
        )
        self.resultaat_unknown = Resultaat.objects.create(
            zaak=self.zaak_unknown,
            _resultaattype_url=(
                "https://andere.catalogus.nl/api/v1/resultaattypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0"
            ),
        )
        self.rol_unknown = Rol.objects.create(
            zaak=self.zaak_unknown,
            _roltype_url="https://andere.catalogus.nl/api/v1/roltypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            betrokkene="https//personen.nl/1",
            betrokkene_type=RolTypes.medewerker,
            roltoelichting="unknown rol",
        )
        self.zaak_eigenschap_unknown = ZaakEigenschap.objects.create(
            zaak=self.zaak_unknown,
            _eigenschap_url="https://andere.catalogus.nl/api/v1/eigenschappen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
            _naam="unknown",
        )
        self.zio_unknown = ZaakInformatieObject.objects.create(
            zaak=self.zaak_unknown,
            _informatieobject_url=(
                "https://andere.documenten.nl/api/v1/informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e"
            ),
        )
        self.zaak_besluit_unknown = ZaakBesluit.objects.create(
            zaak=self.zaak_unknown,
            _besluit_url="https://andere.besluiten.nl/api/v1/besluiten/9b235f85-4f39-49df-ab6e-9c2d32123cf5",
        )

    def test_composite_urls_filled(self):
        # 1. known service -> composite url fields are filled
        self.zaak_known.refresh_from_db()
        self.relevante_zaak_known.refresh_from_db()
        self.status_known.refresh_from_db()
        self.resultaat_known.refresh_from_db()
        self.rol_known.refresh_from_db()
        self.zaak_eigenschap_known.refresh_from_db()
        self.zio_known.refresh_from_db()
        self.zaak_besluit_known.refresh_from_db()

        self.assertEqual(self.zaak_known._zaaktype_base_url.pk, self.ztc_known.pk)
        self.assertEqual(
            self.zaak_known._zaaktype_relative_url,
            "zaaktypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.relevante_zaak_known._relevant_zaak_base_url.pk, self.zrc_known.pk
        )
        self.assertEqual(
            self.relevante_zaak_known._relevant_zaak_relative_url,
            "zaken/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
        )
        self.assertEqual(self.status_known._statustype_base_url.pk, self.ztc_known.pk)
        self.assertEqual(
            self.status_known._statustype_relative_url,
            "statustypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.resultaat_known._resultaattype_base_url.pk, self.ztc_known.pk
        )
        self.assertEqual(
            self.resultaat_known._resultaattype_relative_url,
            "resultaattypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(self.rol_known._roltype_base_url.pk, self.ztc_known.pk)
        self.assertEqual(
            self.rol_known._roltype_relative_url,
            "roltypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.zaak_eigenschap_known._eigenschap_base_url.pk, self.ztc_known.pk
        )
        self.assertEqual(
            self.zaak_eigenschap_known._eigenschap_relative_url,
            "eigenschappen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.zio_known._informatieobject_base_url.pk, self.drc_known.pk
        )
        self.assertEqual(
            self.zio_known._informatieobject_relative_url,
            "informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
        )
        self.assertEqual(
            self.zaak_besluit_known._besluit_base_url.pk, self.brc_known.pk
        )
        self.assertEqual(
            self.zaak_besluit_known._besluit_relative_url,
            "besluiten/9b235f85-4f39-49df-ab6e-9c2d32123cf5",
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
        self.assertTrue(
            Service.objects.filter(
                api_root="https://andere.besluiten.nl/api/v1/"
            ).exists()
        )

        ztc_new = Service.objects.get(api_root="https://andere.catalogus.nl/api/v1/")
        zrc_new = Service.objects.get(api_root="https://andere.zaken.nl/api/v1/")
        drc_new = Service.objects.get(api_root="https://andere.documenten.nl/api/v1/")
        brc_new = Service.objects.get(api_root="https://andere.besluiten.nl/api/v1/")
        for service in [ztc_new, zrc_new, drc_new, brc_new]:
            self.assertEqual(service.label, "FIXME")
            self.assertEqual(service.api_type, APITypes.orc)

        self.zaak_unknown.refresh_from_db()
        self.relevante_zaak_unknown.refresh_from_db()
        self.status_unknown.refresh_from_db()
        self.resultaat_unknown.refresh_from_db()
        self.rol_unknown.refresh_from_db()
        self.zaak_eigenschap_unknown.refresh_from_db()
        self.zio_unknown.refresh_from_db()
        self.zaak_besluit_unknown.refresh_from_db()

        self.assertEqual(self.zaak_unknown._zaaktype_base_url.id, ztc_new.id)
        self.assertEqual(
            self.zaak_unknown._zaaktype_relative_url,
            "zaaktypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.relevante_zaak_unknown._relevant_zaak_base_url.id, zrc_new.id
        )
        self.assertEqual(
            self.relevante_zaak_unknown._relevant_zaak_relative_url,
            "zaken/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
        )
        self.assertEqual(self.status_unknown._statustype_base_url.id, ztc_new.id)
        self.assertEqual(
            self.status_unknown._statustype_relative_url,
            "statustypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(self.resultaat_unknown._resultaattype_base_url.id, ztc_new.id)
        self.assertEqual(
            self.resultaat_unknown._resultaattype_relative_url,
            "resultaattypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(self.rol_unknown._roltype_base_url.id, ztc_new.id)
        self.assertEqual(
            self.rol_unknown._roltype_relative_url,
            "roltypen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(
            self.zaak_eigenschap_unknown._eigenschap_base_url.id, ztc_new.id
        )
        self.assertEqual(
            self.zaak_eigenschap_unknown._eigenschap_relative_url,
            "eigenschappen/7ebd86f8-ce22-4ecf-972b-b2ac20b219c0",
        )
        self.assertEqual(self.zio_unknown._informatieobject_base_url.id, drc_new.id)
        self.assertEqual(
            self.zio_unknown._informatieobject_relative_url,
            "informatieobjecten/50c9a565-51dc-49ec-804c-99ac72f9ae6e",
        )
        self.assertEqual(self.zaak_besluit_unknown._besluit_base_url.id, brc_new.id)
        self.assertEqual(
            self.zaak_besluit_unknown._besluit_relative_url,
            "besluiten/9b235f85-4f39-49df-ab6e-9c2d32123cf5",
        )
