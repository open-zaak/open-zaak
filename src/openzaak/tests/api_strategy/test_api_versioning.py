from django.test import override_settings

import yaml
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

EXPECTED_VERSION = "0.1.0"


class DSOApiStrategyTests(APITestCase):
    def test_api_19_documentation_version_json(self):
        url = reverse("schema-json-authorizations", kwargs={"format": ".json"})

        response = self.client.get(url)

        self.assertIn("application/json", response["Content-Type"])
        doc = response.json()
        self.assertGreaterEqual(doc["openapi"], "3.0.0")

    def test_api_19_documentation_version_yaml(self):
        url = reverse("schema-json-authorizations", kwargs={"format": ".yaml"})

        response = self.client.get(url)

        self.assertIn("application/yaml", response["Content-Type"])
        doc = yaml.safe_load(response.content)
        self.assertGreaterEqual(doc["openapi"], "3.0.0")

    @override_settings(ROOT_URLCONF="openzaak.tests.api_strategy.urls")
    def test_api_24_version_header(self):
        response = self.client.get("/test-view")

        self.assertEqual(response["API-version"], EXPECTED_VERSION)
