# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig
from django.db.models.signals import post_migrate

from rest_framework import serializers


class UtilsConfig(AppConfig):
    name = "openzaak.utils"

    def ready(self):
        from . import checks, fields, lookups, serializer_fields  # noqa
        from .signals import update_admin_index

        post_migrate.connect(update_admin_index, sender=self)

        # register FKOrServiceUrlField drf field
        mapping = serializers.ModelSerializer.serializer_field_mapping
        mapping[fields.FkOrServiceUrlField] = serializer_fields.FKOrServiceUrlField
