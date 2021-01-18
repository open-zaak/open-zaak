# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.core.signals import setting_changed
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save
from django.dispatch import receiver

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject

from .api.viewsets import (
    EnkelvoudigInformatieObjectViewSet,
    GebruiksrechtenViewSet,
    ObjectInformatieObjectViewSet,
)
from .models import EnkelvoudigInformatieObject, Gebruiksrechten, ObjectInformatieObject
from .typing import IORelation
from .utils import private_media_storage_cmis

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], dispatch_uid="documenten.sync_oio")
def sync_oio(
    sender: ModelBase, signal: ModelSignal, instance: IORelation, **kwargs
) -> None:
    """
    Synchronize instances of ObjectInformatieObject with ZIO/BIO.

    Business logic:
    * updates are not allowed
    * creating a BIO or ZIO creates the OIO
    * deleting a BIO or ZIO deletes the OIO
    """
    logger.debug("Received signal %r, from sender %r", signal, sender)

    # we only support BIO/ZIO signals
    if sender not in [BesluitInformatieObject, ZaakInformatieObject]:
        return

    # check for post_save that's not create -> block it
    if signal is post_save:
        created = kwargs["created"]

        # in case of an update, nothing else needs to happen regarding OIOs
        if not created:
            return

        # loading fixtures -> skip
        if kwargs["raw"]:
            return

        ObjectInformatieObject.objects.create_from(instance)

    elif signal is post_delete:
        ObjectInformatieObject.objects.delete_for(instance)

    else:
        raise NotImplementedError(f"Signal {signal} is not supported")


@receiver(setting_changed)
def rerun_cmis_storage_setup(signal: ModelSignal, setting: str, **kwargs) -> None:
    if setting == "CMIS_ENABLED":
        private_media_storage_cmis._setup()
        EnkelvoudigInformatieObjectViewSet.queryset = (
            EnkelvoudigInformatieObject.objects.select_related(
                "canonical", "_informatieobjecttype"
            )
            .order_by("canonical", "-versie")
            .distinct("canonical")
        )
        ObjectInformatieObjectViewSet.queryset = (
            ObjectInformatieObject.objects.select_related(
                "_zaak", "_besluit", "informatieobject"
            )
            .prefetch_related("informatieobject__enkelvoudiginformatieobject_set")
            .all()
        )
        GebruiksrechtenViewSet.queryset = (
            Gebruiksrechten.objects.select_related("informatieobject")
            .prefetch_related("informatieobject__enkelvoudiginformatieobject_set")
            .all()
        )
