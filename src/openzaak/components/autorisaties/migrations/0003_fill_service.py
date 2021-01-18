# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations
from ..middleware import COMPONENT_MAPPING
from zgw_consumers.constants import APITypes, AuthTypes
from urllib.parse import urljoin


def get_api_type(url):
    for component, api_type in COMPONENT_MAPPING.items():
        if component in url:
            return api_type

    for api_type in APITypes.values:
        if api_type in url:
            return api_type

    return APITypes.orc


def upload_services(apps, schema_editor):
    APICredential = apps.get_model("vng_api_common", "APICredential")
    ExternalAPICredential = apps.get_model("autorisaties", "ExternalAPICredential")
    Service = apps.get_model("zgw_consumers", "Service")

    services = []
    for api_credential in APICredential.objects.order_by("pk"):
        # determine api_type
        api_type = get_api_type(api_credential.api_root)
        oas = urljoin(api_credential.api_root, "schema/openapi.yaml")

        services.append(
            Service(
                label=api_credential.label,
                api_root=api_credential.api_root,
                api_type=api_type,
                auth_type=AuthTypes.zgw,
                client_id=api_credential.client_id,
                secret=api_credential.secret,
                oas=oas,
                user_id=api_credential.user_id,
                user_representation=api_credential.user_representation,
            )
        )

    for external_credential in ExternalAPICredential.objects.order_by("pk"):
        oas = urljoin(external_credential.api_root, "schema/openapi.yaml")

        services.append(
            Service(
                label=external_credential.label,
                api_root=external_credential.api_root,
                api_type=APITypes.orc,
                auth_type=AuthTypes.api_key,
                header_key=external_credential.header_key,
                header_value=external_credential.header_value,
                oas=oas,
            )
        )

    Service.objects.bulk_create(services)


class Migration(migrations.Migration):
    dependencies = [
        ("autorisaties", "0002_externalapicredential"),
        ("zgw_consumers", "0009_auto_20200401_0829"),
        ("vng_api_common", "0002_apicredential"),
    ]

    operations = [migrations.RunPython(upload_services, migrations.RunPython.noop)]
