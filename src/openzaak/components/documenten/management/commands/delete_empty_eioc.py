# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from typing import List

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from openzaak.components.documenten.models import EnkelvoudigInformatieObjectCanonical


class Command(BaseCommand):
    help = "Check for any empty document identities (no related document)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help=_("Delete automatically any empties"),
        )

    def handle(self, *args, **options):
        if settings.CMIS_ENABLED:
            self.stdout.write(_("This command does not run with CMIS enabled."))
            return

        msg = _("Checking {count} records ...").format(
            count=EnkelvoudigInformatieObjectCanonical.objects.count()
        )
        self.stdout.write(msg)

        duplicates = EnkelvoudigInformatieObjectCanonical.objects.filter(
            enkelvoudiginformatieobject__isnull=True
        )

        if len(duplicates) == 0:
            self.stdout.write(_("Found no empty records."))
            return

        msg = _("Found {count} empty records.").format(count=len(duplicates))
        self.stdout.write(msg)

        if not options["interactive"]:
            delete_empties(duplicates)
            self.stdout.write(self.style.SUCCESS(_("Deleted all the empties.")))
            return

        while True:
            option = self.get_option()

            if option == 3:
                self.stdout.write(_("Exiting."))
                return
            elif option == 2:
                try:
                    delete_empties(duplicates)
                    self.stdout.write(
                        self.style.SUCCESS(
                            _("Deleted {count} empties document(s).").format(
                                count=len(duplicates)
                            )
                        )
                    )
                    return
                except Exception as e:
                    self.stderr.write(
                        _("An error occurred. No document identities were deleted.")
                    )
                    raise e
            elif option == 1:
                for document_id in duplicates:
                    self.stdout.write(
                        f"* ID: {document_id.id}, " f"Lock: {document_id.lock}"
                    )
            else:
                raise CommandError(_("Invalid option chosen."))

    @staticmethod
    def get_option() -> int:
        message = _(
            "\n1) Show empty records\n"
            "2) Delete empty records\n"
            "3) Quit\n\n"
            "Choose your action [1-3]:\n"
        )

        raw_value = input(message)
        try:
            value = int(raw_value)
        except ValueError:
            raise CommandError(_("Invalid option chosen."))

        return value


@transaction.atomic
def delete_empties(empties: List) -> None:
    for document_id in empties:
        document_id.delete()
    return
