# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.test import tag
from django.urls import reverse

import requests
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from maykin_common.vcr import VCRMixin
from privates.test import temp_private_root

from openzaak.accounts.tests.factories import SuperUserFactory

from ...factories import EnkelvoudigInformatieObjectFactory
from ..mixins import S3torageMixin, upload_to


@temp_private_root()
@disable_admin_mfa()
@tag("gh-2282", "s3-storage")
@patch("privates.fields.PrivateMediaFileField.generate_filename", upload_to)
class EnkelvoudigInformatieObjectDownloadAdminTests(VCRMixin, S3torageMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)
        vcr = self._get_vcr()
        vcr.filter_query_parameters += ("AWSAccessKeyId", "Expires", "Signature")

    def _get_vcr_kwargs(self, **kwargs):
        # Necessary because these parameters are always calculated at the timestamp
        kwargs.update(
            {"filter_query_parameters": ("AWSAccessKeyId", "Expires", "Signature")}
        )
        return super()._get_vcr_kwargs(**kwargs)

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

        # download link points to s3 storage, so we use `requests` instead of `self.app`
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

        # download link points to s3 storage, so we use `requests` instead of `self.app`
        download_response = requests.get(download_link.attrs["href"])
        self.assertEqual(download_response.text, "STUFF")
        self.assertEqual(
            download_response.headers["content-type"], "application/octet-stream"
        )
