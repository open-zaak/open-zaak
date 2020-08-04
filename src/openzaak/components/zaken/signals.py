# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save
from django.dispatch import receiver

from openzaak.components.besluiten.models import Besluit

from .models import ZaakBesluit

logger = logging.getLogger(__name__)


@receiver(
    [post_save, post_delete], sender=Besluit, dispatch_uid="zaken.sync_zaakbesluit"
)
def sync_zaakbesluit(
    sender: ModelBase, signal: ModelSignal, instance: Besluit, **kwargs
) -> None:
    """
    Synchronize instances of ZaakBeslut with Besluit.

    Business logic:
    * updates are not allowed
    * creating a Besluit with zaak creates the ZaakBesluit
    * deleting a Besluit with zaak deletes the ZaakBesluit
    """

    # check for post_save that's not create -> block it
    if signal is post_save:
        # loading fixtures -> skip
        if kwargs["raw"]:
            return

        created = kwargs["created"]

        if not created:
            if instance.zaak == instance.previous_zaak:
                return

            if instance.previous_zaak:
                ZaakBesluit.objects.delete_for(instance, previous=True)

        if instance.zaak:
            ZaakBesluit.objects.create_from(instance)

    elif signal is post_delete:

        if instance.zaak:
            ZaakBesluit.objects.delete_for(instance)

    else:
        raise NotImplementedError(f"Signal {signal} is not supported")
