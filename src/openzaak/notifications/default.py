# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from openzaak.components.zaken.models import ZaakObject


def handle(message: dict) -> None:
    resource = message.get("resource")
    actie = message.get("actie")
    resource_url = message.get("resourceUrl")
    kenmerken = message.get("kenmerken", {})
    objecttype_omschrijving = kenmerken.get("objecttypeOmschrijving")
    zaken_ids = message.get("zaken", [])

    if resource != "object":
        return

    if actie == "create":
        for zaak_id in zaken_ids:
            ZaakObject.objects.get_or_create(
                zaak_id=zaak_id,
                object=resource_url,
                defaults={
                    "object_type": "overig",
                    "object_type_overige": objecttype_omschrijving,
                    "relatieomschrijving": "",
                },
            )

    elif actie == "update":
        existing = ZaakObject.objects.filter(object=resource_url)
        to_keep = set(zaken_ids)
        for obj in existing:
            if obj.zaak_id not in to_keep:
                obj.delete()
        for zaak_id in zaken_ids:
            ZaakObject.objects.get_or_create(
                zaak_id=zaak_id,
                object=resource_url,
                defaults={"object_type": "overig"},
            )

    elif actie == "destroy":
        ZaakObject.objects.filter(object=resource_url).delete()
