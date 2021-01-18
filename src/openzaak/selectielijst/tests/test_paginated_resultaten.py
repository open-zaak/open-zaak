# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlencode

from django.test import TestCase

import requests_mock

from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.utils.tests import ClearCachesMixin

from ..api import get_resultaten
from ..models import ReferentieLijstConfig
from . import mock_oas_get


@requests_mock.Mocker()
class SelectieLijstResultatenTests(
    ReferentieLijstServiceMixin, ClearCachesMixin, TestCase
):
    def test_single_page(self, m):
        ReferentieLijstConfig.get_solo()
        mock_oas_get(m)
        m.get(
            "https://selectielijst.openzaak.nl/api/v1/resultaten",
            json={"previous": None, "next": None, "count": 0, "results": []},
        )

        results = get_resultaten()

        self.assertEqual(results, [])

    def test_multiple_pages(self, m):
        ReferentieLijstConfig.get_solo()
        mock_oas_get(m)
        base_url = "https://selectielijst.openzaak.nl/api/v1/resultaten"
        _results = [
            {"url": f"{base_url}/cc5ae4e3-a9e6-4386-bcee-46be4986a829", "nummer": 1},
            {"url": f"{base_url}/8320ab7d-3a8d-4c8b-b94a-14b4fa374d0a", "nummer": 1},
        ]

        m.get(
            "https://selectielijst.openzaak.nl/api/v1/resultaten",
            json={
                "previous": None,
                "next": f"{base_url}?page=2",
                "count": 1,
                "results": _results[0:1],
            },
            complete_qs=True,
        )
        m.get(
            "https://selectielijst.openzaak.nl/api/v1/resultaten?page=2",
            json={
                "previous": None,
                "next": None,
                "count": 1,
                "results": _results[1:2],
            },
            complete_qs=True,
        )

        results = get_resultaten()

        self.assertEqual(results, _results)

        requests = [
            req
            for req in m.request_history
            if req.path != "/api/v1/schema/openapi.yaml"
        ]
        self.assertEqual(len(requests), 2)

    def test_filter_procestype(self, m):
        ReferentieLijstConfig.get_solo()
        mock_oas_get(m)
        base_url = "https://selectielijst.openzaak.nl/api/v1/resultaten"
        query = urlencode({"procesType": "https://example.com"})
        m.get(
            f"{base_url}?{query}",
            json={"previous": None, "next": None, "count": 0, "results": []},
            complete_qs=True,
        )

        results = get_resultaten("https://example.com")

        self.assertEqual(results, [])
