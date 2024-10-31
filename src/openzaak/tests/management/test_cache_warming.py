# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import shutil
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

import requests_mock
from vng_api_common.oas import fetcher

from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin

from ..utils import (
    ClearCachesMixin,
    mock_brc_oas_get,
    mock_cmc_oas_get,
    mock_drc_oas_get,
    mock_vrc_oas_get,
    mock_zrc_oas_get,
    mock_ztc_oas_get,
)

SCHEMAS = Path(__file__).parent.parent
CACHE_DIR = SCHEMAS / "cache"


@override_settings(BASE_DIR=str(SCHEMAS))
@requests_mock.Mocker()
class WarmCacheCommandTests(SelectieLijstMixin, ClearCachesMixin, TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.addCleanup(lambda: shutil.rmtree(CACHE_DIR, ignore_errors=True))
        self.addCleanup(fetcher.cache.clear)

    def _install_mocks(self, m):
        mock_brc_oas_get(m)
        mock_drc_oas_get(m)
        mock_zrc_oas_get(m)
        mock_ztc_oas_get(m)
        mock_vrc_oas_get(m)
        mock_cmc_oas_get(m)
        mock_selectielijst_oas_get(m)

    def test_successful_cache_warming(self, m):
        CACHE_DIR.mkdir(parents=True)
        self._install_mocks(m)
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "warm_cache", stdout=stdout, stderr=stderr, verbosity=1, no_color=True
        )

        output = stdout.getvalue().splitlines()
        expected_output = [
            "Populating OpenAPI specs cache...",
            "API spec for 'vrl-0.5.6' written.",
            "API spec for 'selectielijst-1.0.0' written.",
            "API spec for 'catalogi-1.2.0' written.",
            "API spec for 'documenten-1.0.1.post1' written.",
            "API spec for 'zaken-1.0.3' written.",
            "API spec for 'besluiten-1.0.1.post0' written.",
            "API spec for 'contactmomenten-2021-09-13' written.",
            "API spec for 'verzoeken-2021-06-21' written.",
        ]
        self.assertEqual(output, expected_output)

        self.assertEqual(stderr.getvalue(), "")

    def test_successful_silent_output(self, m):
        CACHE_DIR.mkdir(parents=True)
        self._install_mocks(m)
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "warm_cache", stdout=stdout, stderr=stderr, verbosity=0, no_color=True
        )

        output = stdout.getvalue().splitlines()
        expected_output = []
        self.assertEqual(output, expected_output)

        self.assertEqual(stderr.getvalue(), "")

    def test_some_errored_some_ok(self, m):
        CACHE_DIR.mkdir(parents=True)
        mock_brc_oas_get(m)
        mock_drc_oas_get(m)
        mock_zrc_oas_get(m)
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "warm_cache", stdout=stdout, stderr=stderr, verbosity=1, no_color=True
        )

        with self.subTest("stdout output"):
            output = stdout.getvalue().splitlines()
            expected_output = [
                "Populating OpenAPI specs cache...",
                "API spec for 'documenten-1.0.1.post1' written.",
                "API spec for 'zaken-1.0.3' written.",
                "API spec for 'besluiten-1.0.1.post0' written.",
            ]
            self.assertEqual(output, expected_output)

        with self.subTest("stderr output"):
            err = stderr.getvalue().splitlines()
            expected_errors = [
                "Failed populating the API spec cache for 'vrl-0.5.6'.",
                "Failed populating the API spec cache for 'selectielijst-1.0.0'.",
                "Failed populating the API spec cache for 'catalogi-1.2.0'.",
                "Failed populating the API spec cache for 'contactmomenten-2021-09-13'.",
                "Failed populating the API spec cache for 'verzoeken-2021-06-21'.",
            ]
            self.assertEqual(err, expected_errors)
