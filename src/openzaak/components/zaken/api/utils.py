from vng_api_common.utils import get_uuid_from_path
from zgw_consumers.client import UnknownService
from zgw_consumers.models import Service


def create_remote_oio(io_url: str, object_url: str, object_type: str = "zaak") -> dict:
    client = Service.get_client(io_url)
    if client is None:
        raise UnknownService(f"{io_url} API should be added to Service model")

    body = {"informatieobject": io_url, "object": object_url, "objectType": object_type}

    response = client.create("objectinformatieobject_create", data=body)
    return response


def delete_remote_oio(oio_url: str) -> None:
    client = Service.get_client(oio_url)
    if client is None:
        raise UnknownService(f"{oio_url} API should be added to Service model")

    client.delete("objectinformatieobject_delete", oio_url)


def create_remote_zaakbesluit(besluit_url: str, zaak_url: str) -> dict:
    client = Service.get_client(zaak_url)
    if client is None:
        raise UnknownService(f"{zaak_url} API should be added to Service model")

    zaak_uuid = get_uuid_from_path(zaak_url)
    body = {"besluit": besluit_url}

    response = client.create("zaakbesluit_create", data=body, zaak_uuid=zaak_uuid)

    return response


def delete_remote_zaakbesluit(zaakbesluit_url: str) -> None:
    client = Service.get_client(zaakbesluit_url)
    if client is None:
        raise UnknownService(f"{zaakbesluit_url} API should be added to Service model")

    client.delete("zaakbesluit_delete", zaakbesluit_url)
