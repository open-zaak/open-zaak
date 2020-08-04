# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models, transaction

from openzaak.components.autorisaties.models import AutorisatieSpec


class SyncAutorisatieManager(models.Manager):
    @transaction.atomic
    def bulk_create(self, *args, **kwargs):
        transaction.on_commit(AutorisatieSpec.sync)
        return super().bulk_create(*args, **kwargs)
