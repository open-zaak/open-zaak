import json
from copy import copy
from uuid import uuid4

from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.selectielijst.tests import mock_oas_get, mock_resource_list
from openzaak.utils.tests import ClearCachesMixin

from ...models import Catalogus
from ..factories import CatalogusFactory

CATALOGUS = {
    "uuid": str(uuid4()),
    "rsin": "000000000",
    "domein": "TEST",
    "contactpersoon_beheer_naam": "test",
    "contactpersoon_beheer_telefoonnummer": "0612345678",
    "contactpersoon_beheer_emailadres": "test@test.nl",
}


class CatalogusAdminImportTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_catalogus_import(self):
        data = json.dumps([CATALOGUS])

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["import_file"] = (
            "bla.json",
            data.encode("utf-8"),
        )
        form["input_format"] = "4"

        response = form.submit()
        response.form.submit()

        imported_catalogus = Catalogus.objects.first()
        self.assertEqual(str(imported_catalogus.uuid), CATALOGUS["uuid"])
        self.assertEqual(imported_catalogus.domein, CATALOGUS["domein"])

    def test_catalogus_import_generate_new_uuid(self):
        data = json.dumps([CATALOGUS])

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["import_file"] = (
            "bla.json",
            data.encode("utf-8"),
        )
        form["input_format"] = "4"
        form["generate_new_uuids"] = "1"

        response = form.submit()
        response.form.submit()

        imported_catalogus = Catalogus.objects.first()
        self.assertNotEqual(str(imported_catalogus.uuid), CATALOGUS["uuid"])
        self.assertEqual(imported_catalogus.domein, CATALOGUS["domein"])

    def test_catalogus_import_update_existing_catalogus(self):
        catalogus = CatalogusFactory.create(**CATALOGUS)

        data = json.dumps([CATALOGUS])

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["import_file"] = (
            "bla.json",
            data.encode("utf-8"),
        )
        form["input_format"] = "4"

        response = form.submit()
        response.form.submit()

        self.assertEqual(Catalogus.objects.count(), 1)

        imported_catalogus = Catalogus.objects.first()
        self.assertEqual(str(imported_catalogus.uuid), str(catalogus.uuid))
        self.assertEqual(imported_catalogus.domein, catalogus.domein)

    def test_catalogus_import_generate_new_uuid_same_domein_updates_existing_catalogus(
        self,
    ):
        catalogus = CatalogusFactory.create(**CATALOGUS)

        new_catalogus = copy(CATALOGUS)
        new_catalogus["contactpersoon_beheer_naam"] = "aangepast"

        data = json.dumps([new_catalogus])

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["import_file"] = (
            "bla.json",
            data.encode("utf-8"),
        )
        form["input_format"] = "4"
        form["generate_new_uuids"] = "1"

        response = form.submit()
        response.form.submit()

        self.assertEqual(Catalogus.objects.count(), 1)

        imported_catalogus = Catalogus.objects.first()
        self.assertEqual(str(imported_catalogus.uuid), CATALOGUS["uuid"])
        self.assertEqual(imported_catalogus.domein, "TEST")
        self.assertEqual(imported_catalogus.contactpersoon_beheer_naam, "aangepast")

    def test_catalogus_import_generate_new_uuid_different_domein_adds_new_catalogus(
        self,
    ):
        catalogus = CatalogusFactory.create(**CATALOGUS)

        new_catalogus = copy(CATALOGUS)
        new_catalogus["domein"] = "TEST2"

        data = json.dumps([new_catalogus])

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["import_file"] = (
            "bla.json",
            data.encode("utf-8"),
        )
        form["input_format"] = "4"
        form["generate_new_uuids"] = "1"

        response = form.submit()
        response.form.submit()

        self.assertEqual(Catalogus.objects.count(), 2)

        imported_catalogus = Catalogus.objects.last()
        self.assertNotEqual(str(imported_catalogus.uuid), CATALOGUS["uuid"])
        self.assertEqual(imported_catalogus.domein, "TEST2")
