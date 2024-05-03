# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from openzaak.utils.webtest import WebTest

from ..api.schema import custom_settings


class BesluitenSchemaTests(WebTest):
    def test_schema_page_title(self):
        response = self.app.get(
            reverse("schema-redoc-besluiten", kwargs={"version": 1})
        )
        self.assertEqual(response.html.find("title").text, custom_settings["TITLE"])
