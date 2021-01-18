# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.utils import get_uuid_from_path
from zgw_consumers.client import UnknownService
from zgw_consumers.models import Service


def create_remote_zaakbesluit(besluit_url: str, zaak_url: str) -> dict:
    client = Service.get_client(zaak_url)
    if client is None:
        raise UnknownService(f"{zaak_url} API should be added to Service model")

    zaak_uuid = get_uuid_from_path(zaak_url)
    body = {"besluit": besluit_url}

    response = client.create("zaakbesluit", data=body, zaak_uuid=zaak_uuid)

    return response


def delete_remote_zaakbesluit(zaakbesluit_url: str) -> None:
    client = Service.get_client(zaakbesluit_url)
    if client is None:
        raise UnknownService(f"{zaakbesluit_url} API should be added to Service model")

    client.delete("zaakbesluit", zaakbesluit_url)
