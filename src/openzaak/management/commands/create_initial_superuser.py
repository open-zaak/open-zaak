# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import os

from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCommand,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--password",
            help="Set the password when the superuser is initially created.",
        )

    def handle(self, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        database = options["database"]
        qs = self.UserModel._default_manager.db_manager(database).filter(
            **{self.UserModel.USERNAME_FIELD: username}
        )
        if qs.exists():
            self.stdout.write("Superuser account already exists, exiting")
            return

        # perform user creation from core Django
        super().handle(**options)

        password = options.get("password") or os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD"
        )
        if password:
            self.stdout.write("Setting user password...")
            user = qs.get()
            user.set_password(password)
            user.save()
