# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.apps import apps
from django.contrib.sites.models import Site
from django.core.management import CommandError, call_command
from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from rest_framework.test import APITestCase

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.models import ResultaatType, StatusType, ZaakType
from openzaak.components.zaken.models import Zaak
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin


class GenerateDataTests(SelectieLijstMixin, APITestCase):
    @requests_mock.Mocker()
    def test_generate_data_yes(self, m):
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
            call_command("generate_data", partition=1, zaaktypen=1, zaken=2)

        # check that the data is generated
        generated_objects_count = {
            "catalogi.Catalogus": 1,
            "catalogi.ZaakType": 1,
            "catalogi.StatusType": 3,
            "catalogi.RolType": 1,
            "catalogi.ResultaatType": 2,
            "catalogi.Eigenschap": 1,
            "zaken.Zaak": 2,
            "zaken.Status": 6,
            "zaken.Rol": 2,
            "zaken.Resultaat": 2,
            "zaken.ZaakEigenschap": 2,
            "zaken.ZaakInformatieObject": 2,
            "zaken.ZaakObject": 2,
            "besluiten.Besluit": 2,
            "besluiten.BesluitInformatieObject": 2,
            "documenten.EnkelvoudigInformatieObjectCanonical": 2,
            "documenten.EnkelvoudigInformatieObject": 2,
            "documenten.ObjectInformatieObject": 4,
        }

        for model_name, obj_count in generated_objects_count.items():
            with self.subTest(model_name):
                model = apps.get_model(model_name)
                self.assertEqual(model.objects.count(), obj_count)

        # assert that some attributes are filled
        # catalogi
        zaaktype = ZaakType.objects.get()
        self.assertTrue(zaaktype.identificatie.startswith("ZAAKTYPE_"))
        self.assertEqual(
            zaaktype.selectielijst_procestype,
            f"{config.service.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )
        # zaken
        for zaak in Zaak.objects.all():
            with self.subTest(zaak):
                self.assertEqual(
                    zaak.selectielijstklasse,
                    f"{config.service.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                )
                self.assertIsNotNone(zaak.archiefactiedatum)

        self.assertEqual(
            StatusType.objects.filter(statustype_omschrijving="").count(), 0
        )

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


@disable_admin_mfa()
class GenerateDataAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

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
