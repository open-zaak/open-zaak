# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import SimpleTestCase

import requests
import requests_mock


@requests_mock.Mocker()
class OutgoingRequestTest(SimpleTestCase):
    def test_outgoing_request_headers(self, m):
        with requests_mock.Mocker() as m:
            m.get("https://example.com/", status_code="200")
            requests.get("https://example.com/")

        headers = m.last_request.headers
        self.assertTrue("User-Agent" in headers)
        self.assertEqual(headers["User-Agent"], "Open Zaak")
