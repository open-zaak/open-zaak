# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations
from zgw_consumers.constants import AuthTypes, APITypes


def upload_nlx(apps, schema_editor):
    URLRewrite = apps.get_model("nlx_url_rewriter", "URLRewrite")
    Service = apps.get_model("zgw_consumers", "Service")

    for url_rewrite in URLRewrite.objects.order_by("pk"):
        from_url = (
            url_rewrite.from_value
            if url_rewrite.from_value.endswith("/")
            else f"{url_rewrite.from_url}/"
        )
        to_url = (
            url_rewrite.to_value
            if url_rewrite.to_value.endswith("/")
            else f"{url_rewrite.to_value}/"
        )

        if Service.objects.filter(api_root=from_url).exists():
            service = Service.objects.get(api_root=from_url)
        else:
            service = Service.objects.create(
                api_root=from_url,
                api_type=APITypes.orc,
                label="from URLRewrite",
                auth_type=AuthTypes.no_auth,
            )

        service.nlx = to_url
        service.save()


class Migration(migrations.Migration):
    dependencies = [
        ("autorisaties", "0004_delete_externalapicredential"),
        ("zgw_consumers", "0008_auto_20200331_1400"),
        ("nlx_url_rewriter", "0001_initial"),
    ]

    operations = [migrations.RunPython(upload_nlx, migrations.RunPython.noop)]
