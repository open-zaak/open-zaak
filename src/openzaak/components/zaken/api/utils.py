# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from vng_api_common.client import to_internal_data

from openzaak.client import get_client
from openzaak.components.zaken.models import ZaakIdentificatie


def create_remote_zaakbesluit(besluit_url: str, zaak_url: str) -> dict:
    client = get_client(zaak_url, raise_exceptions=True)
    body = {"besluit": besluit_url}

    return to_internal_data(client.post(f"{zaak_url}/besluiten", json=body))


def delete_remote_zaakbesluit(zaakbesluit_url: str) -> None:
    client = get_client(zaakbesluit_url, raise_exceptions=True)
    to_internal_data(client.delete(zaakbesluit_url))


def generate_zaak_identificatie_with_creation_year(
    validated_data: dict,
) -> ZaakIdentificatie:
    return ZaakIdentificatie.objects.generate(
        validated_data["bronorganisatie"], date.today()
    )


def generate_zaak_identificatie_with_start_datum_year(
    validated_data: dict,
) -> ZaakIdentificatie:
    return ZaakIdentificatie.objects.generate(
        validated_data["bronorganisatie"], validated_data["startdatum"]
    )
