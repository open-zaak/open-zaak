# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import migrations
from openzaak.utils.migrations import fill_service_urls


def fill_zaken_service_urls(apps, schema_editor):
    Zaak = apps.get_model("zaken", "Zaak")
    RelevanteZaakRelatie = apps.get_model("zaken", "RelevanteZaakRelatie")
    Status = apps.get_model("zaken", "Status")
    Resultaat = apps.get_model("zaken", "Resultaat")
    Rol = apps.get_model("zaken", "Rol")
    ZaakEigenschap = apps.get_model("zaken", "ZaakEigenschap")
    ZaakInformatieObject = apps.get_model("zaken", "ZaakInformatieObject")
    ZaakBesluit = apps.get_model("zaken", "ZaakBesluit")

    fill_service_urls(
        apps,
        Zaak,
        url_field="_zaaktype_url",
        service_base_field="_zaaktype_base_url",
        service_relative_field="_zaaktype_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        RelevanteZaakRelatie,
        url_field="_relevant_zaak_url",
        service_base_field="_relevant_zaak_base_url",
        service_relative_field="_relevant_zaak_relative_url",
    )
    fill_service_urls(
        apps,
        Status,
        url_field="_statustype_url",
        service_base_field="_statustype_base_url",
        service_relative_field="_statustype_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        Resultaat,
        url_field="_resultaattype_url",
        service_base_field="_resultaattype_base_url",
        service_relative_field="_resultaattype_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        Rol,
        url_field="_roltype_url",
        service_base_field="_roltype_base_url",
        service_relative_field="_roltype_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        ZaakEigenschap,
        url_field="_eigenschap_url",
        service_base_field="_eigenschap_base_url",
        service_relative_field="_eigenschap_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        ZaakInformatieObject,
        url_field="_informatieobject_url",
        service_base_field="_informatieobject_base_url",
        service_relative_field="_informatieobject_relative_url",
        fake_etag=True,
    )
    fill_service_urls(
        apps,
        ZaakBesluit,
        url_field="_besluit_url",
        service_base_field="_besluit_base_url",
        service_relative_field="_besluit_relative_url",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("zaken", "0010_auto_20220815_1742"),
    ]

    operations = [
        migrations.RunPython(fill_zaken_service_urls, migrations.RunPython.noop)
    ]
