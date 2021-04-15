# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import io
import os

from django.core.management import call_command
from django.test import TestCase

from openzaak.accounts.models import User


class CreateInitialSuperUserCommandTests(TestCase):
    def test_create_from_cli(self):
        call_command(
            "create_initial_superuser",
            "--username=admin",
            "--password=admin",
            "--email=admin@example.com",
            "--no-input",
            stdout=io.StringIO(),
        )

        user = User.objects.get()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        self.assertEqual(user.username, "admin")
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.check_password("admin"))

    def test_command_noop_if_user_exists(self):
        User.objects.create(username="admin")

        call_command(
            "create_initial_superuser",
            "--username=admin",
            "--password=admin",
            "--email=admin@example.com",
            "--no-input",
            stdout=io.StringIO(),
        )

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertEqual(user.username, "admin")
        self.assertEqual(user.email, "")
        self.assertFalse(user.check_password("admin"))

    def test_password_from_env(self):
        os.environ["DJANGO_SUPERUSER_PASSWORD"] = "admin"

        def reset_env():
            del os.environ["DJANGO_SUPERUSER_PASSWORD"]

        self.addCleanup(reset_env)

        call_command(
            "create_initial_superuser",
            "--username=admin",
            "--email=admin@example.com",
            "--no-input",
            stdout=io.StringIO(),
        )

        user = User.objects.get()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        self.assertEqual(user.username, "admin")
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.check_password("admin"))

    def test_without_password(self):
        call_command(
            "create_initial_superuser",
            "--username=admin",
            "--email=admin@example.com",
            "--no-input",
            stdout=io.StringIO(),
        )

        user = User.objects.get()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        self.assertEqual(user.username, "admin")
        self.assertEqual(user.email, "admin@example.com")
        self.assertFalse(user.check_password("admin"))
