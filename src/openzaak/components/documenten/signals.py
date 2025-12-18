# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save, pre_delete
from django.dispatch import receiver

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject

from .models import EnkelvoudigInformatieObject, ObjectInformatieObject
from .typing import IORelation


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


@receiver(
    post_delete,
    sender=EnkelvoudigInformatieObject,
    dispatch_uid="documenten.delete_eio_file",
)
def delete_eio_file(sender, instance, **kwargs):
    if instance.inhoud:
        instance.inhoud.delete(save=False)


@receiver(
    [pre_delete, post_save],
    sender=EnkelvoudigInformatieObject,
    dispatch_uid="documenten.set_canonical_latest_version",
)
def set_canonical_latest_version(sender, signal, instance, **kwargs):
    if signal is pre_delete:
        instance.canonical.latest_version = (
            instance.canonical.enkelvoudiginformatieobject_set.exclude(
                id=instance.id
            ).first()
        )
        instance.canonical.save()
    elif signal is post_save:
        instance.canonical.latest_version = instance
        instance.canonical.save()
    else:
        raise NotImplementedError(f"Signal {signal} is not supported")
