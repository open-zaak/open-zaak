# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings

import yaml
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

EXPECTED_VERSIONS = (
    ("autorisaties", "1.0.0"),
    ("besluiten", "1.0.0"),
    ("catalogi", "1.0.0"),
    ("documenten", "1.0.0"),
    ("zaken", "1.0.0"),
)


class APIVersioningTests(APITestCase):
    def test_api_19_documentation_version_json(self):
        for component, _ in EXPECTED_VERSIONS:
            with self.subTest(component=component):
                url = reverse(f"schema-json-{component}", kwargs={"format": ".json"})

                response = self.client.get(url)

                self.assertIn("application/json", response["Content-Type"])
                doc = response.json()
                self.assertGreaterEqual(doc["openapi"], "3.0.0")

    def test_api_19_documentation_version_yaml(self):
        for component, _ in EXPECTED_VERSIONS:
            with self.subTest(component=component):
                url = reverse(f"schema-json-{component}", kwargs={"format": ".yaml"})

                response = self.client.get(url)

                self.assertIn("application/yaml", response["Content-Type"])
                doc = yaml.safe_load(response.content)
                self.assertGreaterEqual(doc["openapi"], "3.0.0")

    @patch("openzaak.utils.middleware.get_version_mapping", return_value={"/": "1.0.0"})
    @override_settings(ROOT_URLCONF="openzaak.tests.api_strategy.urls")
    def test_api_24_version_header(self, m):
        response = self.client.get("/test-view")

        self.assertEqual(response["API-version"], "1.0.0")
