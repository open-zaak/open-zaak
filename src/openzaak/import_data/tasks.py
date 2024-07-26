# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from openzaak import celery_app
from openzaak.import_data.models import Import, ImportStatusChoices

logger = logging.getLogger(__name__)


@celery_app.task()
def remove_imports():
    now = timezone.now()

    imports = Import.objects.filter(
        finished_on__lt=now - timedelta(days=settings.IMPORT_RETENTION_DAYS),
        status__in=ImportStatusChoices.deletion_choices,
    )

    logger.info(f"Removing imports {','.join([str(i) for i in imports])}")

    imports.delete()
