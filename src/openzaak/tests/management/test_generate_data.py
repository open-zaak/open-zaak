# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.apps import apps
from django.core.management import CommandError, call_command

import requests_mock
from rest_framework.test import APITestCase

from openzaak.components.catalogi.models import ZaakType
from openzaak.components.zaken.models import Zaak
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_selectielijst_oas_get


class GenerateDataTests(APITestCase):
    @requests_mock.Mocker()
    def test_generate_data_yes(self, m):
        # mocks for Selectielijst API calls
        config = ReferentieLijstConfig.get_solo()
        mock_selectielijst_oas_get(m)
        m.get(
            f"{config.api_root}resultaten",
            json={
                "previous": None,
                "next": None,
                "count": 1,
                "results": [
                    {
                        "url": f"{config.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                        "procesType": f"{config.api_root}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
                        "nummer": 1,
                        "volledigNummer": "1.1",
                        "naam": "Ingericht",
                        "omschrijving": "",
                        "procestermijn": "nihil",
                        "procestermijnWeergave": "Nihil",
                        "bewaartermijn": "P10Y",
                        "toelichting": "Invoering nieuwe werkwijze",
                    }
                ],
            },
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
        self.assertEqual(zaaktype.identificatie, "ZAAKTYPE_0")
        # zaken
        for zaak in Zaak.objects.all():
            with self.subTest(zaak):
                self.assertEqual(
                    zaak.selectielijstklasse,
                    f"{config.api_root}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
                )
                self.assertIsNotNone(zaak.archiefactiedatum)

        # checks external calls
        self.assertEqual(m.last_request.url, f"{config.api_root}resultaten")

    def test_generate_data_no(self):
        with patch("builtins.input", lambda *args: "no"):
            with self.assertRaises(CommandError):
                call_command("generate_data", partition=1, zaaktypen=1, zaken=2)
