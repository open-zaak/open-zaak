# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from unittest.mock import patch
from urllib.parse import urlparse

from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from mozilla_django_oidc_db.models import OpenIDConnectConfig

from .factories import SuperUserFactory


class OIDCLoginButtonTestCase(WebTest):
    def test_oidc_button_disabled(self):
        config = OpenIDConnectConfig.get_solo()
        config.enabled = False
        config.save()

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is not visible
        self.assertIsNone(oidc_login_link)

    def test_oidc_button_enabled(self):
        config = OpenIDConnectConfig.get_solo()
        config.enabled = True
        config.oidc_op_token_endpoint = "https://some.endpoint.nl/"
        config.oidc_op_user_endpoint = "https://some.endpoint.nl/"
        config.oidc_rp_client_id = "id"
        config.oidc_rp_client_secret = "secret"
        config.save()

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is visible
        self.assertIsNotNone(oidc_login_link)
        self.assertEqual(
            oidc_login_link.attrs["href"], reverse("oidc_authentication_init")
        )


class AdminSessionRefreshMiddlewareTests(WebTest):
    @patch(
        "mozilla_django_oidc_db.mixins.OpenIDConnectConfig.get_solo",
        return_value=OpenIDConnectConfig(
            enabled=True, oidc_op_authorization_endpoint="https://example.com/auth/",
        ),
    )
    @patch(
        "mozilla_django_oidc.middleware.SessionRefresh.is_refreshable_url",
        return_value=True,
    )
    def test_session_refresh_no_crash(self, *mocks):
        """
        Regression test for crash on admin login because of session refresh.
        """
        user = SuperUserFactory.create()
        admin_url = reverse("admin:index")

        response = self.app.get(admin_url, user=user)

        # we are being redirected to OIDC
        self.assertEqual(response.status_code, 302)
        redirect_url = urlparse(response["Location"])
        self.assertEqual(redirect_url.scheme, "https")
        self.assertEqual(redirect_url.netloc, "example.com")
        self.assertEqual(redirect_url.path, "/auth/")
