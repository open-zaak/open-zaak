# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import os
import secrets
import string

from django.conf import settings
from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCommand,
)
from django.core.mail import send_mail
from django.urls import reverse


def make_random_password():
    """
    UserModel.objects.make_random_password has been removed.
    https://docs.djangoproject.com/en/4.2/releases/4.2/#id1

    The following implementation was recommended.
    """
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for i in range(20))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and sum(c.isdigit() for c in password) >= 3
        ):
            break

    return password


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--password",
            help="Set the password when the superuser is initially created.",
        )
        parser.add_argument(
            "--generate-password",
            action="store_true",
            help=(
                "Generate and e-mail the password. The --password option and "
                "environment variable overrule this flag."
            ),
        )

    def handle(self, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        database = options["database"]
        qs = self.UserModel._default_manager.db_manager(database).filter(
            **{self.UserModel.USERNAME_FIELD: username}
        )
        if qs.exists():
            self.stdout.write(
                self.style.WARNING("Superuser account already exists, exiting")
            )
            return

        password = options.get("password") or os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD"
        )

        if password or options["generate_password"]:
            options["interactive"] = False

        # perform user creation from core Django
        super().handle(**options)

        user = qs.get()

        if not password and options["generate_password"]:
            password = make_random_password()

        if password:
            self.stdout.write("Setting user password...")
            user.set_password(password)
            user.save()

        if options["generate_password"]:
            try:
                link = f'{settings.ALLOWED_HOSTS[0]}{reverse("admin:index")}'
            except IndexError:
                link = "unknown url"

            send_mail(
                f"Credentials for {settings.PROJECT_NAME} ({link})",
                f"Credentials for project: {settings.PROJECT_NAME}\n\nUsername: {username}\nPassword: {password}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
