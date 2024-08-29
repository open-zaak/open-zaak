# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the error documents configured in Nginx are available.

Nginx configuration:

    error_page  413              /413.json;
    error_page   500 502 503 504  /500.json;
"""

from django.test import TestCase
from django.urls import reverse


class ErrorDocumentTests(TestCase):
    def test_500_response(self):
        url = reverse("errordoc-500")
        self.assertEqual(url, "/500.json")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        self.assertIsInstance(response.json(), dict)

    def test_413_response(self):
        url = reverse("errordoc-413")
        self.assertEqual(url, "/413.json")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 413)
        self.assertIsInstance(response.json(), dict)
