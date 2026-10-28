# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from vng_api_common.caching.etags import EtagUpdate

from .models import BesluitTypeInformatieObjectType


@receiver(
    [post_save, post_delete],
    sender=BesluitTypeInformatieObjectType,
    dispatch_uid="catalogi.btiot_etag_update",
)
def mark_related_resources_for_etag_update(sender, instance, **kwargs) -> None:
    """
    Mark the besluittype and informatieobjecttype for an ETag update when their
    relation row changes.

    ``vng_api_common`` does this by itself for regular related fields (as used for
    ``ZaakType``), but it can't see through the custom list field that
    ``BesluitType.informatieobjecttypen`` uses to return external URLs. Without this
    handler, the besluittype's ETag would go stale.
    """
    if kwargs.get("raw"):
        return

    for field in ("besluittype", "_informatieobjecttype"):
        try:
            related = getattr(instance, field)
        except ObjectDoesNotExist:
            continue

        if related is None:
            continue

        if hasattr(related, "_prefetched_objects_cache"):
            related._prefetched_objects_cache = {}

        EtagUpdate.mark_affected(related)
