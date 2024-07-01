# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext

from django_webtest import WebTest

from openzaak.accounts.tests.factories import RecoveryTokenFactory, SuperUserFactory

LOGIN_URL = reverse_lazy("admin:login")


@override_settings(
    USE_OIDC_FOR_ADMIN_LOGIN=False,
    MAYKIN_2FA_ALLOW_MFA_BYPASS_BACKENDS=[],  # enforce MFA
)
class RecoveryTokenTests(WebTest):
    @tag("gh-4072")
    def test_can_enter_recovery_token(self):
        user = SuperUserFactory.create(
            with_totp_device=True,
            username="admin",
            password="admin",
        )
        recovery_token = RecoveryTokenFactory.create(device__user=user).token
        login_page = self.app.get(LOGIN_URL, auto_follow=True)

        # log in with credentials
        form = login_page.forms["login-form"]
        form["auth-username"] = "admin"
        form["auth-password"] = "admin"
        response = form.submit()

        # we should now be on the enter-your-token page
        form = response.forms["login-form"]
        self.assertIn("token-otp_token", form.fields)

        # do not enter a token, but follow the link to use a recovery token
        link_name = gettext("Use a recovery token")
        recovery_page = response.click(description=link_name)
        self.assertEqual(recovery_page.status_code, 200)

        recovery_form = recovery_page.forms[0]
        recovery_form["backup-otp_token"] = recovery_token
        admin_index = recovery_form.submit().follow()
        self.assertEqual(admin_index.request.path, reverse("admin:index"))
