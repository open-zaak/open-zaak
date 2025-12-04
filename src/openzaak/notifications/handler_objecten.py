# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.db import transaction

import structlog
from django_loose_fk.loaders import BaseLoader
from vng_api_common.constants import CommonResourceAction

KANAAL_OBJECTEN = "objecten"
logger = structlog.stdlib.get_logger(__name__)


@transaction.atomic
def handle(message: dict) -> None:
    from openzaak.components.zaken.models import Zaak, ZaakObject

    kanaal = message.get("kanaal")
    if kanaal != KANAAL_OBJECTEN:
        return

    resource = message.get("resource")
    actie = message.get("actie")
    resource_url = message.get("resourceUrl")
    kenmerken = message.get("kenmerken", {})
    objecttype_omschrijving = kenmerken.get("objecttypeOmschrijving")
    zaken_urls = message.get("zaken", [])

    if resource != "object":
        return

    loader = BaseLoader()
    resolved_zaken_ids = []

    for url in zaken_urls:
        if loader.is_local_url(url):
            try:
                zaak_instance = loader.load_local_object(url, Zaak)
                if zaak_instance:
                    resolved_zaken_ids.append(zaak_instance.pk)
            except Exception:
                continue

    if actie == CommonResourceAction.create:
        existing_ids = set(
            ZaakObject.objects.filter(object=resource_url).values_list(
                "zaak_id", flat=True
            )
        )
        to_create = [
            ZaakObject(
                zaak_id=zaak_id,
                object=resource_url,
                object_type="overig",
                object_type_overige=objecttype_omschrijving,
                # TODO: Should we use the default empty string here?
                relatieomschrijving="",
            )
            for zaak_id in resolved_zaken_ids
            if zaak_id not in existing_ids
        ]
        ZaakObject.objects.bulk_create(to_create)

        if to_create:
            created_zaak_ids = [obj.zaak_id for obj in to_create]
            logger.info(
                "Created %d ZaakObject relation(s) for object '%s' to Zaak IDs: %s",
                len(to_create),
                resource_url,
                created_zaak_ids,
            )

    elif actie == CommonResourceAction.update:
        to_delete_zaak_ids = (
            ZaakObject.objects.filter(object=resource_url)
            .exclude(zaak_id__in=resolved_zaken_ids)
            .values_list("zaak_id", flat=True)
        )

        deleted_count, _ = (
            ZaakObject.objects.filter(object=resource_url)
            .exclude(zaak_id__in=resolved_zaken_ids)
            .delete()
        )

        if deleted_count > 0:
            logger.info(
                "Deleted %d stale ZaakObject relation(s) for object '%s' from Zaak IDs: %s",
                deleted_count,
                resource_url,
                list(to_delete_zaak_ids),
            )

        existing_ids = set(
            ZaakObject.objects.filter(object=resource_url).values_list(
                "zaak_id", flat=True
            )
        )
        to_create = [
            ZaakObject(
                zaak_id=zaak_id,
                object=resource_url,
                object_type="overig",
            )
            for zaak_id in resolved_zaken_ids
            if zaak_id not in existing_ids
        ]
        ZaakObject.objects.bulk_create(to_create)

        if to_create:
            created_zaak_ids = [obj.zaak_id for obj in to_create]
            logger.info(
                "Created %d new ZaakObject relation(s) during update for object '%s' to Zaak IDs: %s",
                len(to_create),
                resource_url,
                created_zaak_ids,
            )

    elif actie == CommonResourceAction.destroy:
        to_delete_zaak_ids = ZaakObject.objects.filter(object=resource_url).values_list(
            "zaak_id", flat=True
        )

        deleted_count, _ = ZaakObject.objects.filter(object=resource_url).delete()

        if deleted_count > 0:
            logger.warning(
                "Deleted %d ZaakObject relation(s) due to object destruction for object '%s' from Zaak IDs: %s",
                deleted_count,
                resource_url,
                list(to_delete_zaak_ids),
            )
