# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.loaders import AuthorizedRequestsLoader

ZAKEN_API = "https://zaken.example.com/api/v1/"
ZAAK = f"{ZAKEN_API}zaken/1"


class AuthorizedRequestsLoaderTests(TestCase):
    def test_negotiates_crs(self):
        """
        A Zaken API answers 412 without ``Accept-Crs`` on zaken, which have geo fields.
        """
        ServiceFactory.create(
            api_type=APITypes.zrc,
            api_root=ZAKEN_API,
            auth_type=AuthTypes.no_auth,
        )

        with requests_mock.Mocker() as m:
            # the last match registered is tried first
            m.get(ZAAK, status_code=412, json={})
            m.get(ZAAK, request_headers={"Accept-Crs": "EPSG:4326"}, json={})

            AuthorizedRequestsLoader.fetch_object(ZAAK)
