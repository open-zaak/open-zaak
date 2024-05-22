# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig
from django.conf import settings
from django.db import models
from django.db.models.signals import post_migrate

from django_loose_fk.virtual_models import HANDLERS, FKHandler
from requests import utils
from rest_framework import serializers


class UtilsConfig(AppConfig):
    name = "openzaak.utils"

    def ready(self):
        from . import (  # noqa
            checks,
            fields,
            handlers,
            lookups,
            oas_extensions,
            serializer_fields,
        )
        from .signals import update_admin_index

        utils.default_user_agent = default_user_agent

        post_migrate.connect(update_admin_index, sender=self)

        # register FKOrServiceUrlField drf field
        mapping = serializers.ModelSerializer.serializer_field_mapping
        mapping[fields.FkOrServiceUrlField] = serializer_fields.FKOrServiceUrlField

        # register FkServiceHandler django-loose-fk handler
        HANDLERS[fields.ServiceFkField] = handlers.FkServiceHandler

        # register one-to-one field (for multi-table inheritance of Zaak)
        HANDLERS[models.OneToOneField] = FKHandler


def default_user_agent(name=settings.USER_AGENT):
    """
    Return a string representing the default user agent.

    :rtype: str
    """
    return str(name)
