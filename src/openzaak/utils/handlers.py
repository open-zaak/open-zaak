# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import models

from django_loose_fk.virtual_models import FKHandler
from zgw_consumers.models import Service


class FkServiceHandler(FKHandler):
    def __get__(self, instance, cls=None) -> models.Model:
        raw_data = instance._loose_fk_data.get(self.field_name, None)

        if isinstance(raw_data, Service):
            return raw_data

        return super().__get__(instance, cls)
