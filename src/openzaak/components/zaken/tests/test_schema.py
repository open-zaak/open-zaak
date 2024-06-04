# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from ..api.schema import custom_settings


@disable_admin_mfa()
class ZakenSchemaTests(WebTest):
    def test_schema_page_title(self):
        response = self.app.get(reverse("schema-redoc-zaken", kwargs={"version": 1}))
        self.assertEqual(response.html.find("title").text, custom_settings["TITLE"])
