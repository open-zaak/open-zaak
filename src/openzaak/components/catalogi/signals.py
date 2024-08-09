# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from typing import Union

from django.db.models.base import ModelBase
from django.db.models.signals import ModelSignal, post_delete
from django.dispatch import receiver

from vng_api_common.authorizations.models import Applicatie, Autorisatie

from openzaak.utils import build_absolute_url

from .models import BesluitType, InformatieObjectType, ZaakType

logger = logging.getLogger(__name__)

FIELD_MAP = {
    ZaakType: "zaaktype",
    InformatieObjectType: "informatieobjecttype",
    BesluitType: "besluittype",
}


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

    filter_kwargs = {FIELD_MAP[type(instance)]: instance_url}

    autorisaties = Autorisatie.objects.filter(**filter_kwargs)
    app_ids = list(autorisaties.values_list("applicatie_id", flat=True))
    autorisaties.delete()

    # well, this is a tricky one! it can happen that this handler deletes the last
    # Autorisatie related to an Applicatie, which essentially makes the Applicatie
    # invalid according to the standard - an application either is superuser, or has
    # autorisaties. Left-overs here would be none of those two options (no superuser, no
    # autorisaties). With #835, this also hides those applications in the API, since
    # they're not valid, which means they cannot be deleted either. This caused the
    # zwg-api-tests postman suite to fail, since there's a call deleting the zaaktype
    # and then a 404'ing call deleting the applicatie.
    #
    # For this reason, since it's effectively deleted in terms of API, we might as well
    # hard-delete the applicatie completely.
    apps_to_delete = Applicatie.objects.filter(
        heeft_alle_autorisaties=False,
        autorisaties__isnull=True,
        # edge case via #1081 and #1080 - if there's a "blueprint", you don't want the
        # entire application to vanish -- this has since been replaced by CatalogusAutorisaties
        catalogusautorisatie__isnull=True,
        id__in=app_ids,
    )
    logger.info("Deleting applications: %s", apps_to_delete)
    apps_to_delete.delete()
