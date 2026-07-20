# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from itertools import groupby

from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from ..api.schema import custom_settings


@disable_admin_mfa()
class DocumentenSchemaTests(WebTest):
    def test_schema_page_title(self):
        response = self.app.get(
            reverse("documenten:schema-redoc-documenten", kwargs={"version": 1})
        )
        self.assertEqual(response.html.find("title").text, custom_settings["TITLE"])

    def test_schema(self):
        vng_query_params = {"page"}
        vng_header_params = {"Content-Type"}

        response = self.app.get(
            reverse("documenten:schema-documenten-json", kwargs={"version": 1})
        )

        zoek_schema = response.json["paths"]["/enkelvoudiginformatieobjecten/_zoek"][
            "post"
        ]
        params_in = {
            in_: set(p["name"] for p in params)
            for in_, params in groupby(zoek_schema["parameters"], key=lambda p: p["in"])
        }

        # non-standard, but works
        extra_params = {"pageSize", "expand"}

        self.assertSetEqual(params_in["header"], vng_header_params)
        self.assertSetEqual(params_in["query"] - extra_params, vng_query_params)
        body_properties = zoek_schema["requestBody"]["content"]["application/json"][
            "schema"
        ]["properties"]

        self.assertSetEqual(
            {"uuid__in", "identificatie", "bronorganisatie", "expand"},
            set(body_properties),
        )
