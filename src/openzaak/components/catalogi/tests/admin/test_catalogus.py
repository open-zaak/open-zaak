# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import CatalogusFactory


@disable_admin_mfa()
class CatalogusAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_catalogus_list_name(self):
        CatalogusFactory.create(naam="test")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "test")

    def test_catalogus_list_placeholder_name(self):
        CatalogusFactory.create(naam="")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "(onbekend)")

    def test_related_object_links(self):
        """
        test that links to related objects in admin list page are valid
        """
        CatalogusFactory.create(naam="test")
        list_url = reverse("admin:catalogi_catalogus_changelist")

        response = self.app.get(list_url)

        self.assertEqual(response.status_code, 200)
        rel_object_links = (
            response.html.find(id="result_list")
            .find(class_="field-_get_object_actions")
            .find_all("a")
        )
        self.assertEqual(len(rel_object_links), 3)
        for link in rel_object_links:
            url = link["href"]
            with self.subTest(url):
                response = self.app.get(url)
                self.assertEqual(response.status_code, 200)
