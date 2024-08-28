# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings

# TODO: remove legacy import of ZGWClient
from zgw_consumers.legacy.client import UnknownService
from zgw_consumers.models import Service

from openzaak.components.documenten.models import ObjectInformatieObject


def delete_remote_resource(resource: str, resource_url: str) -> None:
    client = Service.get_client(resource_url)
    if client is None:
        raise UnknownService(f"{resource_url} API should be added to Service model")

    client.delete(resource, resource_url)


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
    delete_remote_resource("objectinformatieobject", oio_url)


def create_remote_objectcontactmoment(
    contactmoment_url: str, object_url: str, object_type: str = "zaak"
) -> dict:
    client = Service.get_client(contactmoment_url)
    if client is None:
        raise UnknownService(
            f"{contactmoment_url} API should be added to Service model"
        )

    body = {
        "contactmoment": contactmoment_url,
        "object": object_url,
        "objectType": object_type,
    }

    response = client.create("objectcontactmoment", data=body)

    return response


def delete_remote_objectcontactmoment(objectcontactmoment_url: str) -> None:
    delete_remote_resource("objectcontactmoment", objectcontactmoment_url)


def create_remote_objectverzoek(
    verzoek_url: str, object_url: str, object_type: str = "zaak"
) -> dict:
    client = Service.get_client(verzoek_url)
    if client is None:
        raise UnknownService(f"{verzoek_url} API should be added to Service model")

    body = {
        "verzoek": verzoek_url,
        "object": object_url,
        "objectType": object_type,
    }

    response = client.create("objectverzoek", data=body)

    return response


def delete_remote_objectverzoek(objectverzoek_url: str) -> None:
    delete_remote_resource("objectverzoek", objectverzoek_url)
