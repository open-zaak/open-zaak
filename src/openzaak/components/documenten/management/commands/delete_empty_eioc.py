# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from collections.abc import Callable
from typing import List, Type

from django.conf import settings
from django.core.management import BaseCommand
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.models import EnkelvoudigInformatieObjectCanonical
from openzaak.components.zaken.models import ZaakInformatieObject


def delete_eioc_and_relations(
    eioc_model: Type[models.Model],
    zio_model: Type[models.Model],
    bio_model: Type[models.Model],
    log_func: Callable[
        [
            str,
        ],
        None,
    ],
) -> None:
    """
    models are added as parameters to be able to use this function in the migrations with apps.get_model
    """
    msg = "Checking {count} records ...".format(count=eioc_model.objects.count())
    log_func(msg)

    duplicates = eioc_model.objects.filter(enkelvoudiginformatieobject__isnull=True)

    if len(duplicates) == 0:
        log_func("Found no empty records.")
        return

    msg = _("Found {count} empty records.").format(count=len(duplicates))
    log_func(msg)

    related_ziots = zio_model.objects.filter(_informatieobject__in=duplicates)
    related_biots = bio_model.objects.filter(_informatieobject__in=duplicates)

    msg = (
        "Found {biot_count} related BesluitInformatieObject "
        "and ZaakInformatieObject related {ziot_count}."
    ).format(biot_count=related_biots.count(), ziot_count=related_ziots.count())
    log_func(msg)

    with transaction.atomic():
        delete_empties(related_ziots)
        delete_empties(related_biots)
        delete_empties(duplicates)


def delete_empties(empties: List) -> None:
    for document_id in empties:
        document_id.delete()


class Command(BaseCommand):
    help = "Delete any empty Document identities and delete related Besluit/ZaakInformatieObjecten"

    def handle(self, *args, **options):
        if settings.CMIS_ENABLED:
            self.stdout.write("This command does not run with CMIS enabled.")
            return

        delete_eioc_and_relations(
            eioc_model=EnkelvoudigInformatieObjectCanonical,
            zio_model=ZaakInformatieObject,
            bio_model=BesluitInformatieObject,
            log_func=self.stdout.write,
        )
