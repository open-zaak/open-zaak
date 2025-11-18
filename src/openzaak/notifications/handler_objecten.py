# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.db import transaction

from django_loose_fk.loaders import BaseLoader
from vng_api_common.constants import CommonResourceAction

from openzaak.components.zaken.models import Zaak, ZaakObject


@transaction.atomic
def handle(message: dict) -> None:
    kanaal = message.get("kanaal")
    if kanaal != "objects":
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
        # Resolve local zaak URLs
        for url in zaken_urls:
            parsed = urlparse(url)
            if parsed.netloc == "openzaak.example.com":
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
                relatieomschrijving="",
            )
            for zaak_id in resolved_zaken_ids
            if zaak_id not in existing_ids
        ]
        ZaakObject.objects.bulk_create(to_create)

    elif actie == CommonResourceAction.update:
        ZaakObject.objects.filter(object=resource_url).exclude(
            zaak_id__in=resolved_zaken_ids
        ).delete()

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

    elif actie == CommonResourceAction.destroy:
        ZaakObject.objects.filter(object=resource_url).delete()
