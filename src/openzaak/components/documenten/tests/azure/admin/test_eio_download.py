# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse

import requests
from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from maykin_common.vcr import VCRMixin

from openzaak.accounts.tests.factories import SuperUserFactory

from ...factories import EnkelvoudigInformatieObjectFactory
from ..mixins import AzureBlobStorageMixin


@disable_admin_mfa()
@freeze_time("2030-01-01T12:00:00")
@tag("gh-2217", "azure-storage")
class EnkelvoudigInformatieObjectDownloadAdminTests(
    VCRMixin, AzureBlobStorageMixin, WebTest
):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_eio_download_inhoud(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bestandsnaam="iets.txt",
            inhoud__data=b"STUFF",
            inhoud__filename="test_eio_download_inhoud.bin",
        )

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(eio.pk,),
        )
        response = self.app.get(change_url)

        bestand_field = response.html("div", {"class": "field-inhoud"})[0]
        download_link = bestand_field("a")[0]

        self.assertEqual(download_link.text, eio.inhoud.path)

        # download link points to azure storage, so we use `requests` instead of `self.app`
        download_response = requests.get(download_link.attrs["href"])

        self.assertEqual(download_response.text, "STUFF")
        self.assertEqual(
            download_response.headers["content-type"], "application/octet-stream"
        )

    def test_eio_download_inhoud_bestandsnaam_empty(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bestandsnaam="",
            inhoud__data=b"STUFF",
            inhoud__filename="test_eio_download_inhoud_bestandsnaam_empty.bin",
        )

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(eio.pk,),
        )

        response = self.app.get(change_url)

        bestand_field = response.html("div", {"class": "field-inhoud"})[0]

        download_link = bestand_field("a")[0]

        self.assertEqual(download_link.text, eio.inhoud.path)

        # download link points to azure storage, so we use `requests` instead of `self.app`
        download_response = requests.get(download_link.attrs["href"])
        self.assertEqual(download_response.text, "STUFF")
        self.assertEqual(
            download_response.headers["content-type"], "application/octet-stream"
        )
