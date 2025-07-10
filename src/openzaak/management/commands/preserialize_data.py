# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

import structlog
from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.zaken.api.serializers import ZaakSerializer
from openzaak.components.zaken.models import (
    Zaak,
)
from openzaak.utils import get_openzaak_domain

logger = structlog.stdlib.get_logger(__name__)


class Command(BaseCommand):
    help = (
        "Preserialize data for all objects in the database. This preserialized data "
        "will be returned by the API to avoid on the fly serialization."
    )

    # def add_arguments(self, parser):
    #     parser.add_argument(
    #         "--partition",
    #         type=int,
    #         default=10000,
    #         help="Number of objects to create at a time to prevent OOM killer",
    #     )

    @transaction.atomic
    def handle(self, *args, **options):
        # TODO allow many=True
        request = APIRequestFactory().get(
            "/", HTTP_HOST=get_openzaak_domain(), secure=settings.IS_HTTPS
        )
        request.versioning_scheme = URLPathVersioning()
        request.version = "1"

        BATCH_SIZE = 1000
        instances_to_update = []
        total_updated = 0
        objects = Zaak.objects.all()
        # objects = Zaak.objects.filter(_json__isnull=True)
        total_objects = objects.count()

        serializer = ZaakSerializer(context={"request": request, "ignore_json": True})

        for zaak in objects.iterator(chunk_size=1000):
            zaak._json = serializer.to_representation(zaak)
            instances_to_update.append(zaak)

            if len(instances_to_update) >= BATCH_SIZE:
                Zaak.objects.bulk_update(instances_to_update, ["_json"])
                total_updated += BATCH_SIZE
                logger.info(
                    "preserialize_progress",
                    total_updated=total_updated,
                    total_objects=total_objects,
                )
                instances_to_update.clear()

        # Final batch update
        if instances_to_update:
            Zaak.objects.bulk_update(instances_to_update, ["_json"])
            total_updated += len(instances_to_update)
            logger.info(
                "preserialize_progress",
                total_updated=total_updated,
                total_objects=total_objects,
            )
