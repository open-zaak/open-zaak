# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import List

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from openzaak.components.documenten.models import EnkelvoudigInformatieObject


class Command(BaseCommand):
    help = "Check for any duplicate documents (with same identificatie, bronorganisatie and versie)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help=_("Delete automatically any duplicates"),
        )

    def handle(self, *args, **options):
        if settings.CMIS_ENABLED:
            self.stdout.write(_("This command does not run with CMIS enabled."))
            return

        msg = _("Checking {count} records ...").format(
            count=EnkelvoudigInformatieObject.objects.count()
        )
        self.stdout.write(msg)

        duplicates = find_duplicate_eios()

        if len(duplicates) == 0:
            self.stdout.write(_("Found no duplicate records."))
            return

        msg = _("Found {count} duplicate records.").format(count=len(duplicates))
        self.stdout.write(msg)

        if not options["interactive"]:
            delete_duplicates(duplicates)
            self.stdout.write(self.style.SUCCESS(_("Deleted all the duplicates.")))
            return

        while True:
            option = self.get_option()

            if option == 3:
                self.stdout.write(_("Exiting."))
                return
            elif option == 2:
                try:
                    delete_duplicates(duplicates)
                    self.stdout.write(
                        self.style.SUCCESS(
                            _("Deleted {count} duplicate document(s).").format(
                                count=len(duplicates)
                            )
                        )
                    )
                    return
                except Exception as e:
                    self.stderr.write(
                        _("An error occurred. No documents were deleted.")
                    )
                    raise e
            elif option == 1:
                for document in duplicates:
                    self.stdout.write(
                        f"* RSIN: {document.bronorganisatie}, "
                        f"Identificatie: {document.identificatie}, "
                        f"UUID: {document.uuid}"
                    )
            else:
                raise CommandError(_("Invalid option chosen."))

    def get_option(self) -> int:
        message = _(
            "\n1) Show duplicate records\n"
            "2) Delete duplicate records (the oldest record(s) will be deleted).\n"
            "3) Quit\n\n"
            "Choose your action [1-3]:\n"
        )

        raw_value = input(message)
        try:
            value = int(raw_value)
        except ValueError:
            raise CommandError(_("Invalid option chosen."))

        return value


def find_duplicate_eios() -> List[EnkelvoudigInformatieObject]:
    all_documents = EnkelvoudigInformatieObject.objects.order_by("creatiedatum")

    already_seen = set()
    duplicates = []
    for document in all_documents:
        unique_data = (
            document.identificatie,
            document.bronorganisatie,
            document.versie,
        )
        if unique_data in already_seen:
            duplicates.append(document)
        else:
            already_seen.add(unique_data)

    return duplicates


@transaction.atomic
def delete_duplicates(duplicates: List) -> None:
    for document in duplicates:
        document.delete()
    return
