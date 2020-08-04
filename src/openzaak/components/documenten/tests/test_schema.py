# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest

from ..api.schema import info


class DocumentenSchemaTests(WebTest):
    def test_schema_page_title(self):
        response = self.app.get(
            reverse("schema-redoc-documenten", kwargs={"version": 1})
        )
        self.assertEqual(response.html.find("title").text, info.title)
