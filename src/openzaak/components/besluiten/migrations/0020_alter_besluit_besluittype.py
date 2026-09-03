# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogi", "0026_set_P0D_servicenorms_to_none"),
        (
            "besluiten",
            "0019_remove_besluit_besluiten_besluit__besluittype_base_url_and__besluittype_relative_url_filled_and_more",
        ),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="besluit",
            name="besluiten_besluit__besluittype_or__besluittype_base_url_filled",
        ),
        migrations.RemoveConstraint(
            model_name="besluit",
            name="besluiten_besluit__besluittype_base_url_and__besluittype_relative_url_filled",
        ),
        migrations.RenameField(
            model_name="besluit",
            old_name="_besluittype",
            new_name="besluittype",
        ),
        migrations.AlterField(
            model_name="besluit",
            name="besluittype",
            field=models.ForeignKey(
                to="catalogi.besluittype",
                on_delete=django.db.models.deletion.PROTECT,
                help_text="URL-referentie naar het BESLUITTYPE (in de Catalogi API).",
            ),
        ),
        migrations.RemoveField(
            model_name="besluit",
            name="_besluittype_base_url",
        ),
        migrations.RemoveField(
            model_name="besluit",
            name="_besluittype_relative_url",
        ),
        migrations.RemoveField(
            model_name="besluit",
            name="_besluittype_url",
        ),
    ]
