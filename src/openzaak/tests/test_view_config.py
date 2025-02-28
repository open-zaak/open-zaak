# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest
from notifications_api_common.models import NotificationsConfig
from requests.exceptions import ConnectionError
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory


class ViewConfigTestCase(WebTest):
    url = reverse_lazy("view-config")
    api_root = "http://notifications.local/api/v1/"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.config = NotificationsConfig.get_solo()

    def test_view_config_page_no_notifs_service(self):
        self.config.notifications_api_service = None
        self.config.save()

        response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        rows = response.html.findAll("tr")

        # Rows for: header, Site domain and HTTPS and notifications (missing)
        self.assertEqual(len(rows), 4)

    def test_view_config_page_with_incorrect_notifs_service(self):
        self.config.notifications_api_service = ServiceFactory.create(
            api_root=self.api_root,
            api_type=APITypes.nrc,
        )
        self.config.save()

        with requests_mock.Mocker() as m:
            m.get(f"{self.api_root}kanaal", status_code=404)
            response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        rows = response.html.findAll("tr")

        # Rows for: header, Site domain, HTTPS, notifications API, auth for notifs API
        # and notifs API connection
        self.assertEqual(len(rows), 6)
        self.assertIn(self.api_root, rows[3].text)
        self.assertIn(_("Configured"), rows[4].text)
        self.assertIn(
            _("Cannot retrieve kanalen: HTTP {status_code}").format(status_code=404),
            rows[5].text,
        )

    def test_view_config_page_with_unreachable_notifs_service(self):
        self.config.notifications_api_service = ServiceFactory.create(
            api_root=self.api_root,
            api_type=APITypes.nrc,
        )
        self.config.save()

        with requests_mock.Mocker() as m:
            m.get(f"{self.api_root}kanaal", exc=ConnectionError)
            response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        rows = response.html.findAll("tr")

        # Rows for: header, Site domain, HTTPS, notifications API, auth for notifs API
        # and notifs API connection
        self.assertEqual(len(rows), 6)
        self.assertIn(self.api_root, rows[3].text)
        self.assertIn(_("Configured"), rows[4].text)
        self.assertIn(_("Could not connect with NRC"), rows[5].text)

    def test_view_config_page_with_correct_notifs_service(self):
        self.config.notifications_api_service = ServiceFactory.create(
            api_root=self.api_root,
            api_type=APITypes.nrc,
        )
        self.config.save()

        with requests_mock.Mocker() as m:
            m.get(f"{self.api_root}kanaal", json={})
            response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        rows = response.html.findAll("tr")

        # Rows for: header, Site domain, HTTPS, notifications API, auth for notifs API
        # and notifs API connection
        self.assertEqual(len(rows), 6)
        self.assertIn(self.api_root, rows[3].text)
        self.assertIn(_("Configured"), rows[4].text)
        self.assertIn(_("Can retrieve kanalen"), rows[5].text)
