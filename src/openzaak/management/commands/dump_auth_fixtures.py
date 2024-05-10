# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Dump the authorization configuration to a file. "
        "This file can be used as input for a setup configuration step on another instance"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path", type=str, help="Path and filename to write the dump to",
        )

    def handle(self, **options):
        path = options["path"]

        with open(path, "w") as f:
            call_command(
                "dumpdata",
                "authorizations",
                "autorisaties",
                "vng_api_common.jwtsecret",
                natural_foreign=True,
                natural_primary=True,
                format="yaml",
                stdout=f,
            )
