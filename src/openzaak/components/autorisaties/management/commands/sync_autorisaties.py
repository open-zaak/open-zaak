# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.loaders import BaseLoader
from vng_api_common.utils import get_resource_for_path

Autorisatie = apps.get_model("authorizations", "Autorisatie")
is_local_url = BaseLoader().is_local_url


class Command(BaseCommand):
    help = _(
        "Remove any existing authorisations related to zaaktypen that have been removed"
    )

    def handle(self, *args, **options):

        to_delete = []

        for autorisatie in Autorisatie.objects.all():
            if not is_local_url(autorisatie.zaaktype):
                continue

            parsed = urlparse(autorisatie.zaaktype)

            try:
                get_resource_for_path(parsed.path)
            except ObjectDoesNotExist:
                to_delete.append(autorisatie)

        Autorisatie.objects.filter(pk__in=[obj.pk for obj in to_delete]).delete()
