# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.urls import reverse

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import CatalogusFactory


class CatalogusAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_catalogus_list_name(self):
        CatalogusFactory.create(_admin_name="test")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "test")

    def test_catalogus_list_placeholder_name(self):
        CatalogusFactory.create(_admin_name="")

        response = self.app.get(reverse("admin:catalogi_catalogus_changelist"))

        admin_name = response.html.find("th", {"class": "field-get_admin_name"})
        self.assertEqual(admin_name.text, "(onbekend)")
