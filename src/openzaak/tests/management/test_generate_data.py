# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.apps import apps
from django.core.management import CommandError, call_command

from rest_framework.test import APITestCase


class GenerateDataTests(APITestCase):
    def test_generate_data_yes(self):
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
        # catalogi
        for model_name, obj_count in generated_objects_count.items():
            with self.subTest(model_name):
                model = apps.get_model(model_name)
                self.assertEqual(model.objects.count(), obj_count)

    def test_generate_data_no(self):
        with patch("builtins.input", lambda *args: "no"):
            with self.assertRaises(CommandError):
                call_command("generate_data", partition=1, zaaktypen=1, zaken=2)
