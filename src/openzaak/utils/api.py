# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings

from zgw_consumers.client import UnknownService
from zgw_consumers.models import Service

from openzaak.components.documenten.models import ObjectInformatieObject


def create_remote_oio(io_url: str, object_url: str, object_type: str = "zaak") -> dict:
    if settings.CMIS_ENABLED:
        if object_type == "zaak":
            oio = ObjectInformatieObject.objects.create(
                informatieobject=io_url, zaak=object_url, object_type=object_type
            )
        elif object_type == "besluit":
            oio = ObjectInformatieObject.objects.create(
                informatieobject=io_url, besluit=object_url, object_type=object_type
            )

        response = {"url": oio.get_url()}
    else:
        client = Service.get_client(io_url)
        if client is None:
            raise UnknownService(f"{io_url} API should be added to Service model")

        body = {
            "informatieobject": io_url,
            "object": object_url,
            "objectType": object_type,
        }

        response = client.create("objectinformatieobject", data=body)
    return response


def delete_remote_oio(oio_url: str) -> None:
    client = Service.get_client(oio_url)
    if client is None:
        raise UnknownService(f"{oio_url} API should be added to Service model")

    client.delete("objectinformatieobject", oio_url)
