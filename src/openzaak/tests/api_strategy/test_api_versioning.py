from django.test import override_settings

import yaml
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

EXPECTED_VERSIONS = (
    ("authorizations", "0.1.0"),
    ("besluiten", "0.1.0"),
    ("catalogi", "0.1.0"),
    ("documenten", "0.1.0"),
    ("zaken", "0.1.0"),
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

    @override_settings(
        ROOT_URLCONF="openzaak.tests.api_strategy.urls", API_VERSION="1.0.0"
    )
    def test_api_24_version_header(self):
        response = self.client.get("/test-view")

        self.assertEqual(response["API-version"], "1.0.0")
