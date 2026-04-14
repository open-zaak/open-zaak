# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import threading

from django.db import transaction
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

import structlog

from openzaak.components.besluiten.models import Besluit
from openzaak.utils import build_fake_request
from openzaak.utils.cloudevents import get_scheduled_event_registry

from .api.cloudevents import ZAAK_GEMUTEERD, send_zaak_cloudevent
from .models import (
    Resultaat,
    Status,
    SubStatus,
    Zaak,
    ZaakBesluit,
    ZaakInformatieObject,
    ZaakObject,
    ZaakRelatie,
)

logger = structlog.stdlib.get_logger(__name__)

# TODO switch to contextvars?
_signal_local = threading.local()


def schedule_zaak_gemuteerd(instance: Zaak):
    registry = get_scheduled_event_registry()

    registry.setdefault(ZAAK_GEMUTEERD, set())
    if instance.pk in registry[ZAAK_GEMUTEERD]:
        return

    registry[ZAAK_GEMUTEERD].add(instance.pk)

    def send():
        try:
            send_zaak_cloudevent(ZAAK_GEMUTEERD, instance, build_fake_request())
        finally:
            registry[ZAAK_GEMUTEERD].discard(instance.pk)

    transaction.on_commit(send)


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


@receiver(post_save, sender=Zaak, dispatch_uid="zaken.zaak.send_zaak_gemuteerd_event")
def send_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    if created:
        return

    if kwargs.get("update_fields") in (
        frozenset({"laatst_gemuteerd"}),
        frozenset({"laatst_geopend"}),
        frozenset({"_etag"}),
    ):
        return

    schedule_zaak_gemuteerd(instance)


def zaak_related_resource_trigger_zaak_gemuteerd(sender, instance, **kwargs):
    if kwargs.get("update_fields") in (
        frozenset({"_etag"}),
        frozenset({"laatst_gemuteerd"}),
        frozenset({"laatst_geopend"}),
    ):
        return

    zaak = instance.zaak
    zaak.laatst_gemuteerd = timezone.now()
    zaak.save(update_fields=["laatst_gemuteerd"])

    schedule_zaak_gemuteerd(zaak)


_post_save = (
    (Status, "zaken.status.trigger_zaak_gemuteerd"),
    (ZaakInformatieObject, "zaken.zio.trigger_zaak_gemuteerd"),
    (Resultaat, "zaken.resultaat.trigger_zaak_gemuteerd"),
    (SubStatus, "zaken.substatus.trigger_zaak_gemuteerd"),
    (ZaakObject, "zaken.zaakobject.trigger_zaak_gemuteerd"),
)
_pre_delete = (
    (ZaakInformatieObject, "zaken.zio.delete.trigger_zaak_gemuteerd"),
    (ZaakObject, "zaken.zaakobject.delete.trigger_zaak_gemuteerd"),
    (Resultaat, "zaken.resultaat.delete.trigger_zaak_gemuteerd"),
)

for model, dispatch_uid in _post_save:
    post_save.connect(
        zaak_related_resource_trigger_zaak_gemuteerd, model, dispatch_uid=dispatch_uid
    )

for model, dispatch_uid in _pre_delete:
    pre_delete.connect(
        zaak_related_resource_trigger_zaak_gemuteerd, model, dispatch_uid=dispatch_uid
    )
