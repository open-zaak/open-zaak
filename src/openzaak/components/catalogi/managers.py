# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from functools import partial

from django.db import models, transaction

from openzaak.components.autorisaties.models import CatalogusAutorisatie


class SyncAutorisatieManager(models.Manager):
    @transaction.atomic
    def bulk_create(self, objs, *args, **kwargs):
        transaction.on_commit(partial(CatalogusAutorisatie.sync, objs))
        return super().bulk_create(objs, *args, **kwargs)
