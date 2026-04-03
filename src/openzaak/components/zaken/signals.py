# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import contextvars
import threading

from django.db import transaction
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.test import RequestFactory
from django.utils import timezone

import structlog

from openzaak.components.besluiten.models import Besluit
from openzaak.utils import get_openzaak_domain

from .api.cloudevents import ZAAK_GEMUTEERD, send_zaak_cloudevent
from .models import (
    Resultaat,
    Status,
    SubStatus,
    Zaak,
    ZaakBesluit,
    ZaakInformatieObject,
    ZaakRelatie,
)

logger = structlog.stdlib.get_logger(__name__)

# TODO switch to contextvars?
_signal_local = threading.local()


scheduled = contextvars.ContextVar("zaak_scheduled", default=False)


def schedule_zaak_gemuteerd(instance: Zaak):
    if scheduled.get():
        return

    scheduled.set(True)

    def send():
        try:
            factory = RequestFactory()
            # TODO not sure if this works with api gateways, subpath, etc
            # could store the domain in a thread local thing
            request = factory.get("/", HTTP_HOST=get_openzaak_domain())
            send_zaak_cloudevent(ZAAK_GEMUTEERD, instance, request)
        finally:
            scheduled.set(False)

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


# TODO presave?
@receiver(post_save, sender=Zaak, dispatch_uid="zaken.zaak.send_zaak_gemuteerd_event")
def send_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    """"""
    # TODO
    # print(sender, instance, created, kwargs)
    if created:
        return

    # TODO doesnt work for patch on laatst_geopend
    if kwargs.get("update_fields") in (
        frozenset({"laatst_gemuteerd"}),
        frozenset({"laatst_geopend"}),
        frozenset({"_etag"}),
    ):
        return

    # TODO move to pre-save? or model level
    # instance.laatst_gemuteerd = timezone.now()
    # instance.save(update_fields=["laatst_gemuteerd"])

    schedule_zaak_gemuteerd(instance)


# TODO also for related resources
# TODO also delete?
@receiver(
    post_save, sender=Status, dispatch_uid="zaken.status.send_zaak_gemuteerd_event"
)
def send_status_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    if created:
        zaak = instance.zaak
        zaak.laatst_gemuteerd = timezone.now()
        zaak.save(update_fields=["laatst_gemuteerd"])

        schedule_zaak_gemuteerd(zaak)


# TODO check what can be combined


@receiver(
    post_save,
    sender=ZaakInformatieObject,
    dispatch_uid="zaken.zio.send_zaak_gemuteerd_event",
)
def send_zio_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    # if created:
    if kwargs.get("update_fields") in (
        frozenset({"laatst_gemuteerd"}),
        frozenset({"_etag"}),
    ):
        return

    zaak = instance.zaak
    zaak.laatst_gemuteerd = timezone.now()
    zaak.save(update_fields=["laatst_gemuteerd"])

    schedule_zaak_gemuteerd(zaak)


@receiver(
    pre_delete,
    sender=ZaakInformatieObject,
    dispatch_uid="zaken.zio.send_zaak_gemuteerd_event",
)
def send_zio_zaak_gwemuteerd_event(sender, instance, **kwargs):
    # if created:
    if kwargs.get("update_fields") in (
        frozenset({"laatst_gemuteerd"}),
        frozenset({"_etag"}),
    ):
        return

    zaak = instance.zaak
    zaak.laatst_gemuteerd = timezone.now()
    zaak.save(update_fields=["laatst_gemuteerd"])

    schedule_zaak_gemuteerd(zaak)


@receiver(
    post_save,
    sender=Resultaat,
    dispatch_uid="zaken.resultaat.send_zaak_gemuteerd_event",
)
def send_resultaat_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    # if created:
    if kwargs.get("update_fields") in (
        frozenset({"laatst_gemuteerd"}),
        frozenset({"_etag"}),
    ):
        return

    zaak = instance.zaak
    zaak.laatst_gemuteerd = timezone.now()
    zaak.save(update_fields=["laatst_gemuteerd"])

    schedule_zaak_gemuteerd(zaak)


@receiver(
    post_save,
    sender=SubStatus,
    dispatch_uid="zaken.substatus.send_zaak_gemuteerd_event",
)
def send_substatus_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    if created:
        zaak = instance.zaak
        zaak.laatst_gemuteerd = timezone.now()
        zaak.save(update_fields=["laatst_gemuteerd"])

        schedule_zaak_gemuteerd(zaak)
