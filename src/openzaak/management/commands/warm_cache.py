# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.core.management import BaseCommand

from openzaak.api_standards import SPECIFICATIONS


class Command(BaseCommand):
    help = "Populate any and all Open Zaak caches"

    def handle(self, **options):
        verbosity = options["verbosity"]

        # populating api spec caches
        if verbosity > 0:
            self.stdout.write("Populating OpenAPI specs cache...")
        for standard in SPECIFICATIONS.values():
            try:
                standard.write_cache()
            except Exception:
                self.stderr.write(
                    f"Failed populating the API spec cache for '{standard.alias}'."
                )
            else:
                if verbosity > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"API spec for '{standard.alias}' written.")
                    )
