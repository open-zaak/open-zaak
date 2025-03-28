# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve


@override_settings(ALLOWED_HOSTS=["some-domain.local"], DISABLE_2FA=False)
class TwoFactorQRGeneratorTestCase(TestCase):
    def test_qr_code_generator_does_not_use_sites_framework(self):
        """
        Regression test for https://github.com/maykinmedia/open-api-framework/issues/40

        Testing the actual QR code output is too much of a hassle, so instead retrieve
        the view class based on the URL and check if `get_issuer` behaves as expected
        """
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        qr_generator_view_class = resolve("/admin/mfa/qrcode/").func.view_class
        issuer = qr_generator_view_class(
            request=RequestFactory().get("/", headers={"Host": "some-domain.local"})
        ).get_issuer()

        self.assertEqual(issuer, "some-domain.local")
