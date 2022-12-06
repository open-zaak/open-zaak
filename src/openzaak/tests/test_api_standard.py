# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import shutil
from copy import deepcopy
from pathlib import Path

from django.test import SimpleTestCase, override_settings

import requests_mock
from vng_api_common.oas import fetcher
from zgw_consumers.test import mock_service_oas_get, read_schema

from openzaak.api_standards import SPECIFICATIONS, APIStandard

from .utils import ClearCachesMixin

ORIGINAL_SPECIFICATIONS = deepcopy(SPECIFICATIONS)

SCHEMAS = Path(__file__).parent
CACHE_DIR = SCHEMAS / "cache"


def reset_spec_registry():
    SPECIFICATIONS.clear()
    SPECIFICATIONS.update(ORIGINAL_SPECIFICATIONS)


@override_settings(BASE_DIR=str(SCHEMAS))
@requests_mock.Mocker()
class APIStandardTests(ClearCachesMixin, SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(reset_spec_registry)
        self.addCleanup(lambda: shutil.rmtree(CACHE_DIR, ignore_errors=True))
        self.addCleanup(fetcher.cache.clear)

    def test_aliases_must_be_unique(self, m):
        # ok
        APIStandard(alias="empty", oas_url="https://example.com/api/")

        # duplicate - not ok
        with self.assertRaises(ValueError):
            APIStandard(alias="empty", oas_url="https://example.com/api/")

    def test_empty_cache_fetch_network(self, m):
        api_standard = APIStandard(alias="empty", oas_url="https://example.com/api/")
        mock_service_oas_get(m, url="", service="empty", oas_url=api_standard.oas_url)

        schema = api_standard.schema

        self.assertEqual(
            schema,
            {
                "openapi": "3.0.0",
                "info": {
                    "title": "Empty schema for mocking purposes",
                    "description": "",
                },
                "paths": {},
                "components": {},
            },
        )

        with self.subTest("Network call made as fallback"):
            self.assertEqual(len(m.request_history), 1)
            self.assertEqual(m.last_request.url, "https://example.com/api/")

        with self.subTest("Network call result is cached on subsequent access"):
            schema = api_standard.schema

            self.assertEqual(len(m.request_history), 1)

    def test_file_not_read_if_already_present_in_cache(self, m):
        api_standard = APIStandard(alias="empty", oas_url="https://example.com/api/")
        mock_service_oas_get(m, url="", service="empty", oas_url=api_standard.oas_url)
        with self.subTest("initial setup"):
            schema = api_standard.schema
            self.assertEqual(len(m.request_history), 1)
            m.reset()

        # file does not exist
        schema = api_standard.schema

        self.assertEqual(
            schema,
            {
                "openapi": "3.0.0",
                "info": {
                    "title": "Empty schema for mocking purposes",
                    "description": "",
                },
                "paths": {},
                "components": {},
            },
        )
        self.assertEqual(len(m.request_history), 0)

    def test_file_exists_in_cache(self, m):
        # create the cache directory and file
        CACHE_DIR.mkdir(parents=True)
        schema: bytes = read_schema("empty")
        (CACHE_DIR / "empty.yaml").write_bytes(schema)
        api_standard = APIStandard(alias="empty", oas_url="https://example.com/api/")

        schema = api_standard.schema

        self.assertEqual(
            schema,
            {
                "openapi": "3.0.0",
                "info": {
                    "title": "Empty schema for mocking purposes",
                    "description": "",
                },
                "paths": {},
                "components": {},
            },
        )
        self.assertEqual(len(m.request_history), 0)
