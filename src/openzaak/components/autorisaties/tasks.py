# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import transaction

import structlog

from openzaak import celery_app
from openzaak.components.autorisaties.models import Applicatie

logger = structlog.stdlib.get_logger(__name__)


@celery_app.task
@transaction.atomic
def remove_empty_applications():
    """
    Before 2.0 catalogi had a signal on deletes for ZT, BT & IOT
    which would remove autorisaties that would not have any type related to it anymore.
    In 2.0 applications have a direct FK to types, so on_delete=CASCADE
    makes sure that "empty" autorisaties are still removed.

    But the catalogi signal also removed applications that had no autorisaties anymore.

    Originally added a signal on Autorisatie but the admin & api delete and recreate everything on update.

    """
    # TODO this could also check for empty autorisaties even though they should not be able to exist?

    apps_to_delete = Applicatie.objects.filter(
        heeft_alle_autorisaties=False,
        autorisaties__isnull=True,
        catalogusautorisatie__isnull=True,
    )

    app_ids_to_delete = list(apps_to_delete.values_list("id", flat=True))

    logger.info(
        "deleting_applications",
        apps_to_delete=app_ids_to_delete,
    )
    apps_to_delete.delete()
