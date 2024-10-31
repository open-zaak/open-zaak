# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings

from openzaak.client import get_client
from openzaak.components.documenten.models import ObjectInformatieObject


def delete_remote_resource(resource: str, resource_url: str) -> None:
    client = get_client(resource_url)
    client.delete(resource_url)


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
        client = get_client(io_url)

        body = {
            "informatieobject": io_url,
            "object": object_url,
            "objectType": object_type,
        }

        response = client.post("objectinformatieobjecten", json=body)
    return response


def delete_remote_oio(oio_url: str) -> None:
    delete_remote_resource("objectinformatieobject", oio_url)


def create_remote_objectcontactmoment(
    contactmoment_url: str, object_url: str, object_type: str = "zaak"
) -> dict:
    client = get_client(contactmoment_url)

    body = {
        "contactmoment": contactmoment_url,
        "object": object_url,
        "objectType": object_type,
    }

    response = client.post("objectcontactmomenten", json=body)
    return response


def delete_remote_objectcontactmoment(objectcontactmoment_url: str) -> None:
    delete_remote_resource("objectcontactmoment", objectcontactmoment_url)


def create_remote_objectverzoek(
    verzoek_url: str, object_url: str, object_type: str = "zaak"
) -> dict:
    client = get_client(verzoek_url)

    body = {
        "verzoek": verzoek_url,
        "object": object_url,
        "objectType": object_type,
    }

    response = client.post("objectverzoeken", json=body)
    return response


def delete_remote_objectverzoek(objectverzoek_url: str) -> None:
    delete_remote_resource("objectverzoek", objectverzoek_url)
