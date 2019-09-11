import logging

from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save
from django.dispatch import receiver

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject

from .models import ObjectInformatieObject
from .typing import IORelation

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

        # we block update!
        if not created:
            raise RuntimeError("Updates to relation information are not allowed.")

        # loading fixtures -> skip
        if kwargs["raw"]:
            return

        ObjectInformatieObject.objects.create_from(instance)

    elif signal is post_delete:
        ObjectInformatieObject.objects.delete_for(instance)

    else:
        raise NotImplementedError(f"Signal {signal} is not supported")
