# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import threading

from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save
from django.dispatch import receiver

import structlog

from openzaak.components.besluiten.models import Besluit

from .models import ZaakBesluit, ZaakRelatie

logger = structlog.stdlib.get_logger(__name__)
_signal_local = threading.local()


@receiver(
    [post_save, post_delete], sender=Besluit, dispatch_uid="zaken.sync_zaakbesluit"
)
def sync_zaakbesluit(
    sender: ModelBase, signal: ModelSignal, instance: Besluit, **kwargs
) -> None:
    """
    Synchronize instances of ZaakBesluit with Besluit.

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


@receiver(
    post_save, sender=ZaakRelatie, dispatch_uid="zaken.create_reverse_zaakrelatie"
)
def create_reverse_zaakrelatie(sender, instance, created, **kwargs):
    """Ensure reverse relation exists whenever one side is added."""
    if getattr(_signal_local, "skip_reverse_create", False):
        return

    if not created:
        return

    # We can only manage reciprocal relationships for local zaken
    if instance._gerelateerde_zaak:
        reverse_exists = ZaakRelatie.objects.filter(
            zaak=instance._gerelateerde_zaak, _gerelateerde_zaak=instance.zaak
        ).exists()

        if not reverse_exists:
            # Avoid triggering the same signal via create by setting a flag
            _signal_local.skip_reverse_create = True
            try:
                ZaakRelatie.objects.create(
                    zaak=instance._gerelateerde_zaak,
                    _gerelateerde_zaak=instance.zaak,
                )
            finally:
                # Make sure the signal is fired again
                _signal_local.skip_reverse_create = False


@receiver(
    post_delete, sender=ZaakRelatie, dispatch_uid="zaken.delete_reverse_zaakrelatie"
)
def delete_reverse_zaakrelatie(sender, instance, **kwargs):
    """Remove reverse relation when one side is removed."""
    if getattr(_signal_local, "skip_reverse_delete", False):
        return

    # We can only manage reciprocal relationships for local zaken
    if instance._gerelateerde_zaak:
        # Avoid triggering the same signal via delete by setting a flag
        _signal_local.skip_reverse_delete = True
        try:
            ZaakRelatie.objects.filter(
                zaak=instance._gerelateerde_zaak, _gerelateerde_zaak=instance.zaak
            ).delete()
        finally:
            # Make sure the signal is fired again
            _signal_local.skip_reverse_delete = False
