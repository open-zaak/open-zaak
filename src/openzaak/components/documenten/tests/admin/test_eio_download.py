# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import EnkelvoudigInformatieObjectFactory


@override_settings(
    SENDFILE_BACKEND="django_sendfile.backends.simple", CMIS_ENABLED=False
)
class EnkelvoudigInformatieObjectDownloadAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_eio_download_inhoud(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bestandsnaam="iets.txt", inhoud__data=b"STUFF"
        )

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change", args=(eio.pk,),
        )
        response = self.app.get(change_url)

        bestand_field = response.html("div", {"class": "field-inhoud"})[0]
        download_link = bestand_field("a")[0]

        self.assertEqual(download_link.text, "iets.txt")

        download_response = self.app.get(download_link.attrs["href"])
        self.assertEqual(download_response.text, "STUFF")
        self.assertEqual(
            download_response.content_disposition, 'attachment; filename="iets.txt"'
        )

    def test_eio_download_inhoud_bestandsnaam_empty(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bestandsnaam="", inhoud__data=b"STUFF"
        )

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change", args=(eio.pk,),
        )
        response = self.app.get(change_url)

        bestand_field = response.html("div", {"class": "field-inhoud"})[0]
        download_link = bestand_field("a")[0]

        self.assertEqual(download_link.text, eio.inhoud.name)

        download_response = self.app.get(download_link.attrs["href"])
        self.assertEqual(download_response.text, "STUFF")
        self.assertEqual(download_response.content_disposition, "attachment")
