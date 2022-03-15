# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import logging

from django.core.cache import caches
from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete, post_save, pre_delete
from django.dispatch import receiver

from vng_api_common.tests import reverse
from zgw_consumers.models import Service

from openzaak.components.besluiten.models import Besluit
from openzaak.utils import build_absolute_url

from .models import ZaakBesluit, ZaakContactMoment

logger = logging.getLogger(__name__)


class SyncError(Exception):
    pass


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


def sync_create_zaakcontactmoment(relation: ZaakContactMoment):
    zaak_url = build_absolute_url(
        reverse("zaak-detail", kwargs={"uuid": relation.zaak.uuid})
    )

    logger.info("Zaak: %s", zaak_url)
    logger.info("Contactmoment: %s", relation.contactmoment)

    # Define the remote resource with which we need to interact
    resource = "objectcontactmoment"
    client = Service.get_client(relation.contactmoment)

    try:
        response = client.create(
            resource,
            {
                "object": zaak_url,
                "contactmoment": relation.contactmoment,
                "objectType": "zaak",
            },
        )
    except Exception as exc:
        logger.error("Could not create remote relation", exc_info=1)
        raise SyncError("Could not create remote relation") from exc

    # save ZaakBesluit url for delete signal
    relation._objectcontactmoment = response["url"]
    relation.save()


def sync_delete_zaakcontactmoment(relation: ZaakContactMoment):
    resource = "objectinformatieobject"
    client = Service.get_client(relation.contactmoment)

    try:
        client.delete(resource, url=relation._objectcontactmoment)
    except Exception as exc:
        logger.error("Could not delete remote relation", exc_info=1)
        raise SyncError("Could not delete remote relation") from exc


@receiver(
    [post_save, pre_delete],
    sender=ZaakContactMoment,
    dispatch_uid="sync.sync_contactmoment_relation",
)
def sync_contactmoment_relation(sender, instance: ZaakContactMoment = None, **kwargs):
    signal = kwargs["signal"]
    if signal is post_save and not instance._objectcontactmoment:
        sync_create_zaakcontactmoment(instance)
    elif signal is pre_delete and instance._objectcontactmoment:
        cache = caches["kic_sync"]
        marked_zcms = cache.get("zcms_marked_for_delete")
        if marked_zcms:
            cache.set("zcms_marked_for_delete", marked_zcms + [instance.uuid])
        else:
            cache.set("zcms_marked_for_delete", [instance.uuid])

        try:
            sync_delete_zaakcontactmoment(instance)
        finally:
            marked_zcms = cache.get("zcms_marked_for_delete")
            marked_zcms.remove(instance.uuid)
            cache.set("zcms_marked_for_delete", marked_zcms)
