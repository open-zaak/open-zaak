# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.client import get_client


def create_remote_zaakbesluit(besluit_url: str, zaak_url: str) -> dict:
    client = get_client(zaak_url)
    body = {"besluit": besluit_url}

    # TODO: is this (nested) constructed URL correct? see get_zaakbesluit_response
    return client.post(f"{zaak_url}/besluiten", json=body)


def delete_remote_zaakbesluit(zaakbesluit_url: str) -> None:
    client = get_client(zaakbesluit_url)
    client.delete(zaakbesluit_url)
