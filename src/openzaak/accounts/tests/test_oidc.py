# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
"""
Test authentication to the admin with OpenID Connect.

Some of these tests use VCR. When re-recording, making sure to:

.. code-block:: bash

    cd docker
    docker compose -f docker-compose.keycloak.yml up

to bring up a Keycloak instance.
"""

from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_common.vcr import VCRMixin
from mozilla_django_oidc_db.models import OIDCClient
from mozilla_django_oidc_db.tests.mixins import OIDCMixin
from mozilla_django_oidc_db.tests.utils import keycloak_login

from ..models import User
from .factories import OIDCClientFactory, StaffUserFactory


class OIDCLoginButtonTestCase(OIDCMixin, WebTest):
    def test_oidc_button_disabled(self):
        OIDCClientFactory.create(
            with_keycloak_provider=True,
            with_admin=True,
            with_admin_options=True,
            enabled=False,
        )

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is not visible
        self.assertIsNone(oidc_login_link)

    def test_oidc_button_enabled(self):
        OIDCClientFactory.create(
            with_keycloak_provider=True,
            with_admin=True,
            with_admin_options=True,
        )

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is visible
        self.assertIsNotNone(oidc_login_link)
        self.assertEqual(
            oidc_login_link.attrs["href"], reverse("oidc_authentication_init")
        )

    def test_config_not_found(self):
        assert not OIDCClient.objects.exists()

        response = self.app.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is not visible
        self.assertIsNone(oidc_login_link)


class OIDCFlowTests(OIDCMixin, VCRMixin, WebTest):
    def test_duplicate_email_unique_constraint_violated(self):
        OIDCClientFactory.create(
            with_keycloak_provider=True,
            with_admin=True,
            with_admin_options=True,
        )

        # this user collides on the email address
        staff_user = StaffUserFactory.create(
            username="no-match", email="admin@example.com"
        )
        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302
        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        error_page = self.app.get(redirect_uri, auto_follow=True)

        with self.subTest("error page"):
            self.assertEqual(error_page.status_code, 200)
            self.assertEqual(error_page.request.path, reverse("admin-oidc-error"))
            self.assertEqual(
                error_page.context["oidc_error"],
                'duplicate key value violates unique constraint "filled_email_unique"'
                "\nDETAIL:  Key (email)=(admin@example.com) already exists.",
            )
            self.assertContains(
                error_page, "duplicate key value violates unique constraint"
            )

        with self.subTest("user state unmodified"):
            self.assertEqual(User.objects.count(), 1)
            staff_user.refresh_from_db()
            self.assertEqual(staff_user.username, "no-match")
            self.assertEqual(staff_user.email, "admin@example.com")
            self.assertTrue(staff_user.is_staff)

    def test_happy_flow(self):
        oidc_client = OIDCClientFactory.create(
            with_keycloak_provider=True,
            with_admin=True,
            with_admin_options=True,
        )
        oidc_client.options["user_settings"]["claim_mappings"]["username"] = [
            "preferred_username"
        ]
        oidc_client.save()

        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302

        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        admin_index = self.app.get(redirect_uri, auto_follow=True)

        self.assertEqual(admin_index.status_code, 200)
        self.assertEqual(admin_index.request.path, reverse("admin:index"))

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.username, "admin")

    def test_happy_flow_existing_user(self):
        oidc_client = OIDCClientFactory.create(
            with_keycloak_provider=True,
            with_admin=True,
            with_admin_options=True,
        )
        oidc_client.options["user_settings"]["claim_mappings"]["username"] = [
            "preferred_username"
        ]
        oidc_client.save()

        staff_user = StaffUserFactory.create(username="admin", email="update-me")
        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302
        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        admin_index = self.app.get(redirect_uri, auto_follow=True)

        self.assertEqual(admin_index.status_code, 200)
        self.assertEqual(admin_index.request.path, reverse("admin:index"))

        self.assertEqual(User.objects.count(), 1)
        staff_user.refresh_from_db()
        self.assertEqual(staff_user.username, "admin")
        self.assertEqual(staff_user.email, "admin@example.com")
