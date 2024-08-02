# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from typing import List

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.models import EnkelvoudigInformatieObjectCanonical
from openzaak.components.zaken.models import ZaakInformatieObject


class Command(BaseCommand):
    help = "Check for any empty document identities (no related document)."

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

        related_ziots = ZaakInformatieObject.objects.filter(
            _informatieobject__in=duplicates
        )
        related_biots = BesluitInformatieObject.objects.filter(
            _informatieobject__in=duplicates
        )

        msg = _(
            "Found {biot_count} related BesluitInformatieObject and ZaakInformatieObject related {ziot_count}."
        ).format(biot_count=related_biots.count(), ziot_count=related_ziots.count())
        self.stdout.write(msg)

        delete_empties(related_ziots)
        delete_empties(related_biots)
        delete_empties(duplicates)


@transaction.atomic
def delete_empties(empties: List) -> None:
    for document_id in empties:
        document_id.delete()
    return
