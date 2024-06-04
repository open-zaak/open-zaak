# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import json
import random
from pathlib import Path
from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import NLXDirectories
from zgw_consumers.models import NLXConfig

from openzaak.tests.utils import AdminTestMixin

from ..forms import get_nlx_choices

CURRENT_DIR = Path(__file__).parent

DEMO_DIRECTORY = "https://directory.demo.nlx.io/"


@disable_admin_mfa()
class NLXConfigTests(AdminTestMixin, WebTest):
    url = reverse_lazy("config:config-nlx")

    def test_outway_invalid_address(self):
        config_page = self.app.get(self.url, user=self.user)
        form = config_page.form

        form["outway"] = "https://invalid-host.local:1337"
        response = form.submit()

        # form validation errors -> no redirect
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            field=None,
            errors=_("Connection refused. Please provide a correct address."),
        )

    @patch(
        "openzaak.config.forms.NLXConfig.get_solo",
        return_value=NLXConfig(
            directory=NLXDirectories.demo, outway="http://my-outway:8080/"
        ),
    )
    @requests_mock.Mocker()
    def test_get_nlx_service_dropdown_choices(self, mock_get_solo, m):
        with open(CURRENT_DIR / "demo-directory.json") as infile:
            m.get(
                f"{DEMO_DIRECTORY}api/directory/list-services", json=json.load(infile)
            )

        choices = get_nlx_choices()

        self.assertEqual(
            choices,
            {
                "Gemeente Stijns": {
                    "http://my-outway:8080/12345678901234567890/parkeerrechten": {
                        "service_name": "parkeerrechten",
                        "oas": "https://nlx.io",
                    },
                },
                "RvRD": {
                    "http://my-outway:8080/12345678901234567891/basisregister-fictieve-kentekens": {
                        "service_name": "basisregister-fictieve-kentekens",
                        "oas": "https://nlx.io",
                    },
                    "http://my-outway:8080/12345678901234567891/basisregister-fictieve-personen": {
                        "service_name": "basisregister-fictieve-personen",
                        "oas": "https://nlx.io",
                    },
                },
            },
        )

    @patch(
        "openzaak.config.forms.NLXConfig.get_solo",
        return_value=NLXConfig(directory=NLXDirectories.demo, outway=""),
    )
    def test_get_nlx_service_no_outway_configured(self, mock_get_solo):
        choices = get_nlx_choices()

        self.assertEqual(choices, {})

    @patch(
        "openzaak.config.forms.NLXConfig.get_solo",
        return_value=NLXConfig(
            directory=NLXDirectories.demo, outway="http://my-outway:8080/"
        ),
    )
    @requests_mock.Mocker()
    def test_get_nlx_service_some_error(self, mock_get_solo, m):
        m.get(
            f"{DEMO_DIRECTORY}api/directory/list-services",
            status_code=random.choice([500, 502, 503]),
        )

        choices = get_nlx_choices()

        self.assertEqual(choices, {})
