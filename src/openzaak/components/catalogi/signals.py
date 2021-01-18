# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from typing import Union

from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete
from django.dispatch import receiver

from vng_api_common.authorizations.models import Autorisatie

from openzaak.utils import build_absolute_url

from .models import BesluitType, InformatieObjectType, ZaakType

logger = logging.getLogger(__name__)


@receiver(
    post_delete, sender=ZaakType, dispatch_uid="catalogi.sync_autorisaties_zaaktype"
)
@receiver(
    post_delete,
    sender=InformatieObjectType,
    dispatch_uid="catalogi.sync_autorisaties_informatieobjecttype",
)
@receiver(
    post_delete,
    sender=BesluitType,
    dispatch_uid="catalogi.sync_autorisaties_besluittype",
)
def sync_autorisaties(
    sender: ModelBase,
    signal: ModelSignal,
    instance: Union[ZaakType, InformatieObjectType, BesluitType],
    **kwargs
) -> None:
    logger.debug("Received signal %r, from sender %r", signal, sender)

    instance_path = instance.get_absolute_api_url()
    instance_url = build_absolute_url(instance_path)
    Autorisatie.objects.filter(zaaktype=instance_url).delete()
