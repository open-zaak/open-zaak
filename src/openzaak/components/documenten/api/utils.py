from django.conf import settings

from rest_framework.reverse import reverse
from zgw_consumers.client import UnknownService
from zgw_consumers.models import Service

from openzaak.utils import build_absolute_url


# TODO: move to general purpose utils
def get_absolute_url(url_name: str, uuid: str) -> str:
    path = reverse(
        url_name,
        kwargs={"version": settings.REST_FRAMEWORK["DEFAULT_VERSION"], "uuid": uuid},
    )
    return build_absolute_url(path)


def create_remote_oio(io_url: str, object_url: str, object_type: str = "zaak") -> dict:
    client = Service.get_client(io_url)
    if client is None:
        raise UnknownService(f"{io_url} API should be added to Service model")

    body = {"informatieobject": io_url, "object": object_url, "objectType": object_type}

    response = client.create("objectinformatieobject", data=body)
    return response


def delete_remote_oio(oio_url: str) -> None:
    client = Service.get_client(oio_url)
    if client is None:
        raise UnknownService(f"{oio_url} API should be added to Service model")

    client.delete("objectinformatieobject", oio_url)
