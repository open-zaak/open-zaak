# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import List
from urllib.parse import urlparse

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.loaders import BaseLoader
from vng_api_common.utils import get_resource_for_path

Autorisatie = apps.get_model("authorizations", "Autorisatie")
is_local_url = BaseLoader().is_local_url


def get_out_of_sync_autorisaties(field: str) -> List[Autorisatie]:
    to_delete = []
    for autorisatie in Autorisatie.objects.exclude(**{field: ""}):
        value = getattr(autorisatie, field)
        if not is_local_url(value):
            continue

        parsed = urlparse(value)

        try:
            get_resource_for_path(parsed.path)
        except ObjectDoesNotExist:
            to_delete.append(autorisatie)
    return to_delete


class Command(BaseCommand):
    help = _(
        "Remove any existing authorisations related to zaaktypen that have been removed"
    )

    def handle(self, *args, **options):
        to_delete = []
        for field in ["zaaktype", "informatieobjecttype", "besluittype"]:
            to_delete += get_out_of_sync_autorisaties(field)

        Autorisatie.objects.filter(pk__in=[obj.pk for obj in to_delete]).delete()
