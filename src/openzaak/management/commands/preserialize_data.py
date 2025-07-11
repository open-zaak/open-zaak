# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

import structlog
from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.zaken.api.serializers import ZaakSerializer
from openzaak.components.catalogi.api.serializers import ZaakTypeSerializer
from openzaak.components.zaken.models import (
    Zaak,
)
from openzaak.components.catalogi.models import ZaakType
from openzaak.utils import get_openzaak_domain

logger = structlog.stdlib.get_logger(__name__)


MODELS = [
    (Zaak, ZaakSerializer,),
    # (ZaakType, ZaakTypeSerializer,)
]

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

        for model, serializer_class in MODELS:
            instances_to_update = []
            total_updated = 0
            objects = model.objects.all()
            # objects = Zaak.objects.filter(_json__isnull=True)
            total_objects = objects.count()

            for batch_start in range(0, total_objects, BATCH_SIZE):
                batch = list(objects[batch_start : batch_start + BATCH_SIZE])

                serializer = serializer_class(
                    batch, many=True, context={"request": request, "ignore_json": True}
                )
                serialized_data = serializer.data

                for zaak, data in zip(batch, serialized_data):
                    zaak._json = data

                model.objects.bulk_update(batch, ["_json"])
                total_updated += len(batch)

                logger.info(
                    "preserialize_progress",
                    total_updated=total_updated,
                    total_objects=total_objects,
                )

            # Final batch update
            if instances_to_update:
                model.objects.bulk_update(instances_to_update, ["_json"])
                total_updated += len(instances_to_update)
                logger.info(
                    "preserialize_progress",
                    total_updated=total_updated,
                    total_objects=total_objects,
                )
