# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete
from django.dispatch import receiver

from vng_api_common.authorizations.models import Autorisatie

from openzaak.components.catalogi.models.zaaktype import ZaakType

logger = logging.getLogger(__name__)


@receiver(post_delete, dispatch_uid="catalogi.sync_autorisaties")
def sync_autorisaties(
    sender: ModelBase, signal: ModelSignal, instance: ZaakType, **kwargs
) -> None:
    logger.debug("Received signal %r, from sender %r", signal, sender)

    if sender is not ZaakType:
        return

    instance_path = instance.get_absolute_api_url()
    site = Site.objects.get_current()
    protocol = "https" if getattr(settings, "IS_HTTPS", True) else "http"
    instance_url = f"{protocol}://{site.domain}{instance_path}"
    Autorisatie.objects.filter(zaaktype=instance_url).delete()
