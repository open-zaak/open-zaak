# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from django.db import migrations, models


def m2m_to_through(apps, schema_editor):
    BesluitType = apps.get_model("catalogi", "BesluitType")
    BesluitTypeInformatieObjectType = apps.get_model(
        "catalogi", "BesluitTypeInformatieObjectType"
    )
    Through = BesluitType.informatieobjecttypen.through

    BesluitTypeInformatieObjectType.objects.bulk_create(
        [
            BesluitTypeInformatieObjectType(
                besluittype_id=row.besluittype_id,
                _informatieobjecttype_id=row.informatieobjecttype_id,
            )
            for row in Through.objects.all().iterator()
        ],
        batch_size=1000,
        ignore_conflicts=True,
    )


def through_to_m2m(apps, schema_editor):
    """
    Restore the M2M table. Relations to external informatieobjecttypen can't be
    represented and are dropped.
    """
    BesluitType = apps.get_model("catalogi", "BesluitType")
    BesluitTypeInformatieObjectType = apps.get_model(
        "catalogi", "BesluitTypeInformatieObjectType"
    )
    Through = BesluitType.informatieobjecttypen.through

    Through.objects.bulk_create(
        [
            Through(
                besluittype_id=row.besluittype_id,
                informatieobjecttype_id=row._informatieobjecttype_id,
            )
            for row in BesluitTypeInformatieObjectType.objects.filter(
                _informatieobjecttype__isnull=False
            ).iterator()
        ],
        batch_size=1000,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalogi", "0028_informatieobjecttype_loose_fk"),
    ]

    operations = [
        migrations.RunPython(m2m_to_through, through_to_m2m),
        migrations.RemoveField(
            model_name="besluittype",
            name="informatieobjecttypen",
        ),
        migrations.AddField(
            model_name="informatieobjecttype",
            name="besluittypen",
            field=models.ManyToManyField(
                blank=True,
                help_text="BESLUITTYPE waarin besluiten van dit BESLUITTYPE worden vastgelegd in informatieobjecten van dit INFORMATIEOBJECTTYPE",
                related_name="informatieobjecttypen",
                through="catalogi.BesluitTypeInformatieObjectType",
                through_fields=("_informatieobjecttype", "besluittype"),
                to="catalogi.besluittype",
            ),
        ),
    ]
