# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import migrations
from urllib.parse import urlsplit, urlunsplit
from django.db.models.functions import Length


def get_service(model, url: str):
    split_url = urlsplit(url)
    scheme_and_domain = urlunsplit(split_url[:2] + ("", "", ""))

    candidates = (
        model.objects.filter(api_root__startswith=scheme_and_domain)
        .annotate(api_root_length=Length("api_root"))
        .order_by("-api_root_length")
    )

    # select the one matching
    for candidate in candidates.iterator():
        if url.startswith(candidate.api_root):
            return candidate

    return None


def fill_service_url(apps, schema_editor):
    Besluit = apps.get_model("besluiten", "Besluit")
    Service = apps.get_model("zgw_consumers", "Service")

    for besluit in Besluit.objects.exclude(_besluittype_url=""):
        url = besluit._besluittype_url
        service = get_service(Service, url)
        relative_url = url[len(service.api_root) :]

        besluit._besluittype_base_url = service
        besluit._besluittype_relative_url = relative_url
        besluit.save()


class Migration(migrations.Migration):
    dependencies = [
        ("besluiten", "0007_auto_20220804_1522"),
    ]

    operations = [migrations.RunPython(fill_service_url, migrations.RunPython.noop)]
