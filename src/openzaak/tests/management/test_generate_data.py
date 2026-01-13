# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.apps import apps
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.autorisaties.api.scopes import (
    SCOPE_AUTORISATIES_BIJWERKEN,
    SCOPE_AUTORISATIES_LEZEN,
)
from openzaak.components.autorisaties.models import Applicatie
from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
    SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
    SCOPE_BESLUITEN_BIJWERKEN,
)
from openzaak.components.catalogi.api.scopes import (
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
    ResultaatType,
    StatusType,
    ZaakType,
)
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_LOCK,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.components.zaken.models import Zaak
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin


class GenerateDataTests(SelectieLijstMixin, APITestCase):
    def setUp(self):
        super().setUp()

        # mocks for Selectielijst API calls
        self.config = ReferentieLijstConfig.get_solo()
        m = requests_mock.Mocker()
        mock_selectielijst_oas_get(m)
        m.get(
            f"{self.config.service.api_root}resultaten",
            json={
                "previous": None,
                "next": None,
                "count": 1,
                "results": [
                    {
                        "url": f"{self.config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                        "procesType": f"{self.config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                        "nummer": 1,
                        "volledigNummer": "1.1",
                        "naam": "Ingericht",
                        "omschrijving": "",
                        "procestermijn": "nihil",
                        "procestermijnWeergave": "Nihil",
                        "bewaartermijn": "P10Y",
                        "toelichting": "Invoering nieuwe werkwijze",
                        "waardering": "vernietigen",
                    }
                ],
            },
        )
        m.get(
            f"{self.config.service.api_root}resultaattypeomschrijvingen",
            json=[
                {
                    "url": (
                        f"{self.config.service.api_root}resultaattypeomschrijvingen"
                        "/ce8cf476-0b59-496f-8eee-957a7c6e2506"
                    ),
                    "omschrijving": "Afgebroken",
                    "definitie": "Afgebroken",
                    "opmerking": "",
                },
                {
                    "url": (
                        f"{self.config.service.api_root}resultaattypeomschrijvingen"
                        "/7cb315fb-4f7b-4a43-aca1-e4522e4c73b3"
                    ),
                    "omschrijving": "Afgehandeld",
                    "definitie": "Afgehandeld",
                    "opmerking": "",
                },
            ],
        )
        m.start()
        self.addCleanup(m.stop)

    @override_settings(
        SITE_DOMAIN="openzaak.local", ALLOWED_HOSTS=["openzaak.local", "testserver"]
    )
    def test_generate_data_yes(self):
        with patch("builtins.input", lambda *args: "yes"):
            call_command(
                "generate_data",
                partition=1,
                zaaktypen=30,
                zaken=30,
            )

        # check that the data is generated
        generated_objects_count = {
            "catalogi.Catalogus": 1,
            "catalogi.ZaakType": 30,
            "catalogi.StatusType": 90,
            "catalogi.RolType": 30,
            "catalogi.ResultaatType": 60,
            "catalogi.Eigenschap": 30,
            "zaken.Zaak": 30,
            "zaken.Status": 90,
            "zaken.Rol": 30,
            "zaken.Resultaat": 30,
            "zaken.ZaakEigenschap": 30,
            "zaken.ZaakInformatieObject": 30,
            "zaken.ZaakObject": 30,
            "besluiten.Besluit": 30,
            "besluiten.BesluitInformatieObject": 30,
            "documenten.EnkelvoudigInformatieObjectCanonical": 30,
            "documenten.EnkelvoudigInformatieObject": 30,
            "documenten.ObjectInformatieObject": 60,
        }

        for model_name, obj_count in generated_objects_count.items():
            with self.subTest(model_name):
                model = apps.get_model(model_name)
                self.assertEqual(model.objects.count(), obj_count)

        # assert that some attributes are filled
        # catalogi
        zaaktype = ZaakType.objects.order_by("pk").first()
        self.assertTrue(zaaktype.identificatie.startswith("ZAAKTYPE_"))
        self.assertEqual(
            zaaktype.selectielijst_procestype,
            f"{self.config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )

        # zaken
        for zaak in Zaak.objects.all():
            with self.subTest(zaak):
                self.assertEqual(
                    zaak.selectielijstklasse,
                    f"{self.config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                )
                self.assertIsNotNone(zaak.archiefactiedatum)
                self.assertIsNotNone(zaak.zaakgeometrie)

        self.assertEqual(
            StatusType.objects.filter(statustype_omschrijving="").count(), 0
        )

    @override_settings(
        SITE_DOMAIN="openzaak.local", ALLOWED_HOSTS=["openzaak.local", "testserver"]
    )
    def test_generate_data_with_superuser_credentials(self):
        with patch("builtins.input", lambda *args: "yes"):
            call_command(
                "generate_data",
                partition=1,
                zaaktypen=30,
                zaken=30,
                generate_superuser_credentials=True,
            )

        with self.subTest("generate superuser credentials"):
            credential = JWTSecret.objects.get(identifier="superuser")
            self.assertEqual(credential.secret, "superuser")

            applicatie = Applicatie.objects.get(client_ids=["superuser"])
            self.assertEqual(applicatie.heeft_alle_autorisaties, True)

    @override_settings(
        SITE_DOMAIN="openzaak.local", ALLOWED_HOSTS=["openzaak.local", "testserver"]
    )
    def test_generate_data_with_non_superuser_credentials(self):
        with patch("builtins.input", lambda *args: "yes"):
            call_command(
                "generate_data",
                partition=1,
                zaaktypen=30,
                zaken=30,
                generate_non_superuser_credentials=True,
            )

        zaaktype = ZaakType.objects.order_by("pk").first()
        iotype = InformatieObjectType.objects.order_by("pk").first()
        besluittype = BesluitType.objects.order_by("pk").first()

        with self.subTest("generate non superuser credentials"):
            credential = JWTSecret.objects.get(identifier="non_superuser")
            self.assertEqual(credential.secret, "non_superuser")

            applicatie = Applicatie.objects.get(client_ids=["non_superuser"])

            self.assertEqual(applicatie.heeft_alle_autorisaties, False)

            zrc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.zrc
            )

            self.assertEqual(zrc_autorisaties.count(), 15)

            autorisatie = zrc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_ZAKEN_ALLES_LEZEN),
                    str(SCOPE_ZAKEN_ALLES_VERWIJDEREN),
                    str(SCOPE_ZAKEN_CREATE),
                    str(SCOPE_ZAKEN_BIJWERKEN),
                ],
            )
            self.assertEqual(
                autorisatie.max_vertrouwelijkheidaanduiding,
                VertrouwelijkheidsAanduiding.zeer_geheim,
            )
            zaaktype_uri = reverse(
                "zaaktype-detail", kwargs={"uuid": zaaktype.uuid, "version": 1}
            )
            self.assertEqual(
                autorisatie.zaaktype, f"http://openzaak.local{zaaktype_uri}"
            )

            drc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.drc
            )

            self.assertEqual(drc_autorisaties.count(), 15)

            autorisatie = drc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_DOCUMENTEN_AANMAKEN),
                    str(SCOPE_DOCUMENTEN_ALLES_LEZEN),
                    str(SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN),
                    str(SCOPE_DOCUMENTEN_BIJWERKEN),
                    str(SCOPE_DOCUMENTEN_LOCK),
                ],
            )
            self.assertEqual(
                autorisatie.max_vertrouwelijkheidaanduiding,
                VertrouwelijkheidsAanduiding.zeer_geheim,
            )
            iotype_uri = reverse(
                "informatieobjecttype-detail",
                kwargs={"uuid": iotype.uuid, "version": 1},
            )
            self.assertEqual(
                autorisatie.informatieobjecttype, f"http://openzaak.local{iotype_uri}"
            )

            brc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.brc
            )

            self.assertEqual(brc_autorisaties.count(), 15)

            autorisatie = brc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_BESLUITEN_BIJWERKEN),
                    str(SCOPE_BESLUITEN_AANMAKEN),
                    str(SCOPE_BESLUITEN_ALLES_LEZEN),
                    str(SCOPE_BESLUITEN_ALLES_VERWIJDEREN),
                ],
            )
            besluittype_uri = reverse(
                "besluittype-detail",
                kwargs={"uuid": besluittype.uuid, "version": 1},
            )
            self.assertEqual(
                autorisatie.besluittype, f"http://openzaak.local{besluittype_uri}"
            )

            ztc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.ztc
            )

            self.assertEqual(ztc_autorisaties.count(), 1)

            autorisatie = ztc_autorisaties.get()
            self.assertEqual(
                autorisatie.scopes,
                [str(SCOPE_CATALOGI_READ), str(SCOPE_CATALOGI_WRITE)],
            )

            ac_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.ac
            )

            self.assertEqual(ac_autorisaties.count(), 1)

            autorisatie = ac_autorisaties.get()
            self.assertEqual(
                autorisatie.scopes,
                [str(SCOPE_AUTORISATIES_BIJWERKEN), str(SCOPE_AUTORISATIES_LEZEN)],
            )

        with self.subTest("generate non superuser credentials for many zaaktypen"):
            credential = JWTSecret.objects.get(identifier="non_superuser_many_types")
            self.assertEqual(credential.secret, "non_superuser_many_types")

            applicatie = Applicatie.objects.get(client_ids=["non_superuser_many_types"])

            self.assertEqual(applicatie.heeft_alle_autorisaties, False)

            zrc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.zrc
            )

            self.assertEqual(zrc_autorisaties.count(), 25)

            autorisatie = zrc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_ZAKEN_ALLES_LEZEN),
                    str(SCOPE_ZAKEN_ALLES_VERWIJDEREN),
                    str(SCOPE_ZAKEN_CREATE),
                    str(SCOPE_ZAKEN_BIJWERKEN),
                ],
            )
            self.assertEqual(
                autorisatie.max_vertrouwelijkheidaanduiding,
                VertrouwelijkheidsAanduiding.zeer_geheim,
            )
            zaaktype_uri = reverse(
                "zaaktype-detail", kwargs={"uuid": zaaktype.uuid, "version": 1}
            )
            self.assertEqual(
                autorisatie.zaaktype, f"http://openzaak.local{zaaktype_uri}"
            )

            drc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.drc
            )

            self.assertEqual(drc_autorisaties.count(), 25)

            autorisatie = drc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_DOCUMENTEN_AANMAKEN),
                    str(SCOPE_DOCUMENTEN_ALLES_LEZEN),
                    str(SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN),
                    str(SCOPE_DOCUMENTEN_BIJWERKEN),
                    str(SCOPE_DOCUMENTEN_LOCK),
                ],
            )
            self.assertEqual(
                autorisatie.max_vertrouwelijkheidaanduiding,
                VertrouwelijkheidsAanduiding.zeer_geheim,
            )
            iotype_uri = reverse(
                "informatieobjecttype-detail",
                kwargs={"uuid": iotype.uuid, "version": 1},
            )
            self.assertEqual(
                autorisatie.informatieobjecttype, f"http://openzaak.local{iotype_uri}"
            )

            brc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.brc
            )

            self.assertEqual(brc_autorisaties.count(), 25)

            autorisatie = brc_autorisaties.order_by("pk").first()
            self.assertEqual(
                autorisatie.scopes,
                [
                    str(SCOPE_BESLUITEN_BIJWERKEN),
                    str(SCOPE_BESLUITEN_AANMAKEN),
                    str(SCOPE_BESLUITEN_ALLES_LEZEN),
                    str(SCOPE_BESLUITEN_ALLES_VERWIJDEREN),
                ],
            )
            besluittype_uri = reverse(
                "besluittype-detail",
                kwargs={"uuid": besluittype.uuid, "version": 1},
            )
            self.assertEqual(
                autorisatie.besluittype, f"http://openzaak.local{besluittype_uri}"
            )

            ztc_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.ztc
            )

            self.assertEqual(ztc_autorisaties.count(), 1)

            autorisatie = ztc_autorisaties.get()
            self.assertEqual(
                autorisatie.scopes,
                [str(SCOPE_CATALOGI_READ), str(SCOPE_CATALOGI_WRITE)],
            )

            ac_autorisaties = applicatie.autorisaties.filter(
                component=ComponentTypes.ac
            )

            self.assertEqual(ac_autorisaties.count(), 1)

            autorisatie = ac_autorisaties.get()
            self.assertEqual(
                autorisatie.scopes,
                [str(SCOPE_AUTORISATIES_BIJWERKEN), str(SCOPE_AUTORISATIES_LEZEN)],
            )

    @requests_mock.Mocker()
    def test_generate_data_without_zaakgeometrie(self, m):
        """
        Assert that it is possible to generate Zaken without zaakgeometrie
        """
        # mocks for Selectielijst API calls
        config = ReferentieLijstConfig.get_solo()
        mock_selectielijst_oas_get(m)
        m.get(
            f"{config.service.api_root}resultaten",
            json={
                "previous": None,
                "next": None,
                "count": 1,
                "results": [
                    {
                        "url": f"{config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                        "procesType": f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                        "nummer": 1,
                        "volledigNummer": "1.1",
                        "naam": "Ingericht",
                        "omschrijving": "",
                        "procestermijn": "nihil",
                        "procestermijnWeergave": "Nihil",
                        "bewaartermijn": "P10Y",
                        "toelichting": "Invoering nieuwe werkwijze",
                        "waardering": "vernietigen",
                    }
                ],
            },
        )
        m.get(
            f"{config.service.api_root}resultaattypeomschrijvingen",
            json=[
                {
                    "url": (
                        f"{config.service.api_root}resultaattypeomschrijvingen"
                        "/ce8cf476-0b59-496f-8eee-957a7c6e2506"
                    ),
                    "omschrijving": "Afgebroken",
                    "definitie": "Afgebroken",
                    "opmerking": "",
                },
                {
                    "url": (
                        f"{config.service.api_root}resultaattypeomschrijvingen"
                        "/7cb315fb-4f7b-4a43-aca1-e4522e4c73b3"
                    ),
                    "omschrijving": "Afgehandeld",
                    "definitie": "Afgehandeld",
                    "opmerking": "",
                },
            ],
        )

        with patch("builtins.input", lambda *args: "yes"):
            call_command(
                "generate_data",
                partition=1,
                zaaktypen=1,
                zaken=1,
                without_zaakgeometrie=True,
            )

        zaak = Zaak.objects.get()

        self.assertIsNone(zaak.zaakgeometrie)

    def test_generate_data_no(self):
        with patch("builtins.input", lambda *args: "no"):
            with self.assertRaises(CommandError):
                call_command("generate_data", partition=1, zaaktypen=1, zaken=2)

    @requests_mock.Mocker()
    def test_generate_data_sl_error(self, m):
        # mocks for Selectielijst API calls
        config = ReferentieLijstConfig.get_solo()
        mock_selectielijst_oas_get(m)
        m.get(f"{config.service.api_root}resultaten", status_code=404)

        with patch("builtins.input", lambda *args: "yes"):
            with self.assertRaises(CommandError):
                call_command("generate_data", partition=1, zaaktypen=1, zaken=2)

    @override_settings(
        SITE_DOMAIN="openzaak.local", ALLOWED_HOSTS=["openzaak.local", "testserver"]
    )
    def test_generate_data_document_only(self):
        with patch("builtins.input", lambda *args: "yes"):
            call_command(
                "generate_data",
                zaaktypen=1,
                zaken=1,
                document_only=True,
            )

            # check that the data is generated
            generated_objects_count = {
                "catalogi.Catalogus": 1,
                "catalogi.ZaakType": 1,
                "catalogi.StatusType": 3,
                "catalogi.RolType": 1,
                "catalogi.ResultaatType": 2,
                "catalogi.Eigenschap": 1,
                "documenten.EnkelvoudigInformatieObjectCanonical": 1,
                "documenten.EnkelvoudigInformatieObject": 1,
            }

            for model_name, obj_count in generated_objects_count.items():
                with self.subTest(model_name):
                    model = apps.get_model(model_name)
                    self.assertEqual(model.objects.count(), obj_count)


@disable_admin_mfa()
@override_settings(SITE_DOMAIN="testserver")
class GenerateDataAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    @requests_mock.Mocker()
    def test_resultaattype_admin(self, m):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1798
        """
        config = ReferentieLijstConfig.get_solo()
        mock_selectielijst_oas_get(m)
        m.get(
            f"{config.service.api_root}resultaten",
            json={
                "previous": None,
                "next": None,
                "count": 1,
                "results": [
                    {
                        "url": f"{config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                        "procesType": f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                        "nummer": 1,
                        "volledigNummer": "1.1",
                        "naam": "Ingericht",
                        "omschrijving": "",
                        "procestermijn": "nihil",
                        "procestermijnWeergave": "Nihil",
                        "bewaartermijn": "P10Y",
                        "toelichting": "Invoering nieuwe werkwijze",
                        "waardering": "vernietigen",
                    }
                ],
            },
        )
        m.get(
            f"{config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
            json={
                "url": f"{config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                "procesType": f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                "nummer": 1,
                "volledigNummer": "1.1",
                "naam": "Ingericht",
                "omschrijving": "",
                "procestermijn": "nihil",
                "procestermijnWeergave": "Nihil",
                "bewaartermijn": "P10Y",
                "toelichting": "Invoering nieuwe werkwijze",
                "waardering": "vernietigen",
            },
        )
        m.get(
            f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
            json={
                "url": f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                "nummer": 1,
                "jaar": 2017,
                "naam": "Instellen en inrichten organisatie",
                "omschrijving": "Instellen en inrichten organisatie",
                "toelichting": "Dit procestype betreft het instellen van een nieuw organisatieonderdeel",
                "procesobject": "De vastgestelde organisatie inrichting",
            },
        )
        m.get(
            f"{config.service.api_root}resultaattypeomschrijvingen",
            json=[
                {
                    "url": (
                        f"{config.service.api_root}resultaattypeomschrijvingen"
                        "/ce8cf476-0b59-496f-8eee-957a7c6e2506"
                    ),
                    "omschrijving": "Afgebroken",
                    "definitie": "Afgebroken",
                    "opmerking": "",
                },
            ],
        )
        m.get(
            (
                f"{config.service.api_root}resultaattypeomschrijvingen"
                "/ce8cf476-0b59-496f-8eee-957a7c6e2506"
            ),
            json={
                "url": f"{config.service.api_root}resultaattypeomschrijvingen"
                "/ce8cf476-0b59-496f-8eee-957a7c6e2506",
                "omschrijving": "Afgebroken",
                "definitie": "Afgebroken",
                "opmerking": "",
            },
        )

        with patch("builtins.input", lambda *args: "yes"):
            call_command("generate_data", partition=1, zaaktypen=1, zaken=2)

        self.assertEqual(ResultaatType.objects.count(), 2)

        for resultaattype in ResultaatType.objects.all():
            with self.subTest(resultaattype):
                self.assertIsNotNone(resultaattype.resultaattypeomschrijving)

                response = self.app.get(
                    reverse(
                        "admin:catalogi_resultaattype_change", args=(resultaattype.pk,)
                    )
                )
                self.assertEqual(response.status_code, 200)
