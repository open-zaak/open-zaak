# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from datetime import UTC, datetime
from unittest.mock import patch

from django.urls import reverse

from django_webtest import WebTest


class WSGITests(WebTest):
    setup_auth = False

    def setUp(self):
        super().setUp()
        from openzaak.wsgi import application

        # Send requests through Open Zaak's WSGI entry point.
        self.app.app = application

    def test_wsgi_application_renders_home_page(self) -> None:
        home = self.app.get(reverse("home"), status=200)

        links = {str(link["href"]).strip() for link in home.html.select("a[href]")}
        for route in (
            "index-zaken",
            "index-besluiten",
            "index-documenten",
            "index-catalogi",
            "index-autorisaties",
        ):
            with self.subTest(route=route):
                self.assertIn(reverse(route), links)

    def test_wsgi_application_sets_utc_timestamp_for_uwsgi_on_error_response(
        self,
    ) -> None:
        with patch("maykin_common.logging.wsgi.uwsgi") as uwsgi:
            before_request = datetime.now(UTC)
            response = self.app.get(reverse("errordoc-413"), status=413)
            after_request = datetime.now(UTC)

        self.assertEqual(response.json["status"], 413)
        uwsgi.set_logvar.assert_called_once()
        name, value = uwsgi.set_logvar.call_args.args
        timestamp = datetime.fromisoformat(value)
        self.assertEqual(name, "iso8601timestamp")
        self.assertEqual(timestamp.tzinfo, UTC)
        self.assertLessEqual(before_request, timestamp)
        self.assertLessEqual(timestamp, after_request)
