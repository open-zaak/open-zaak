# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging

from django.db import transaction

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.authorizations.serializers import (
    ApplicatieSerializer as _ApplicatieSerializer,
)
from vng_api_common.models import JWTSecret

logger = logging.getLogger(__name__)


class ApplicatieSerializer(_ApplicatieSerializer):
    def create_missing_credentials(self, applicatie: Applicatie):
        # create missing jwtsecret objects for admin page
        current_credentials = list(
            JWTSecret.objects.filter(identifier__in=applicatie.client_ids).values_list(
                "identifier", flat=True
            )
        )
        new_credentials = []
        for client_id in applicatie.client_ids:
            if client_id not in current_credentials:
                new_credentials.append(JWTSecret(identifier=client_id, secret=""))

        JWTSecret.objects.bulk_create(new_credentials)

    @transaction.atomic
    def create(self, validated_data):
        applicatie = super().create(validated_data)
        self.create_missing_credentials(applicatie)

        return applicatie

    @transaction.atomic
    def update(self, instance, validated_data):
        applicatie = super().update(instance, validated_data)
        self.create_missing_credentials(applicatie)

        return applicatie
