# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib import admin
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from maykin_common.vcr import VCRMixin
from requests.exceptions import RequestException
from webtest import Upload

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.admin import EnkelvoudigInformatieObjectAdmin
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
)
from openzaak.components.documenten.widgets import AdminFileWidget

from ....storage import documenten_storage
from ...factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from ..mixins import AzureBlobStorageMixin


@freeze_time("2025-12-01T12:00:00")
@tag("gh-2217", "azure-storage")
@disable_admin_mfa()
class EnkelvoudigInformatieObjectAdminTests(VCRMixin, AzureBlobStorageMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_form_widget(self):
        admin_obj = EnkelvoudigInformatieObjectAdmin(
            EnkelvoudigInformatieObject, admin.site
        )
        form = admin_obj.get_form(None)()
        self.assertIsInstance(form.fields["inhoud"].widget, AdminFileWidget)

    def test_add_informatieobject_page(self):
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        self.assertEqual(response.status_code, 200)

    def test_create_informatieobject_save(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.forms["enkelvoudiginformatieobject_form"]

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"foo")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 302)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.canonical, canonical)
        self.assertEqual(eio.inhoud.read(), b"foo")
        self.assertTrue(documenten_storage.exists(eio.inhoud.name))

    def test_create_informatieobject_save_azure_request_exception(self):
        """
        If no connection could be made with Azure, the admin form should raise errors
        for the `inhoud` field
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.forms["enkelvoudiginformatieobject_form"]

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload(
            "test_create_informatieobject_save_azure_timeout.txt", b"foo"
        )

        with self.vcr_raises(RequestException):
            response = form.submit(name="_continue")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["errors"],
            [
                [
                    _(
                        "Something went wrong while trying to write the file to Azure Blob Storage"
                    )
                ]
            ],
        )
        self.assertFalse(EnkelvoudigInformatieObject.objects.exists())

    def test_get_informatieobject_shows_current_file_path(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud__filename="test_get_informatieobject.bin"
        )
        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change", args=(eio.pk,)
        )

        response = self.app.get(change_url)

        self.assertEqual(response.status_code, 200)

        current_file = response.html.find("p", {"class": "file-upload"})

        self.assertIn(eio.inhoud.path, current_file.text)

        download_link = current_file.find("a").attrs["href"]

        # Verify that the download link points to Azurite
        self.assertTrue(
            download_link.startswith(
                "http://127.0.0.1:10000/devstoreaccount1/openzaak/documenten"
            )
        )
