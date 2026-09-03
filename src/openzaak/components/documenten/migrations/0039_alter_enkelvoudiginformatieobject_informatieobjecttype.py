# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogi", "0026_set_P0D_servicenorms_to_none"),
        ("documenten", "0038_alter_bestandsdeel_inhoud"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="enkelvoudiginformatieobject",
            name="documenten_enkelvoudiginformatieobject__informatieobjecttype_or__informatieobjecttype_base_url_filled",
        ),
        migrations.RemoveConstraint(
            model_name="enkelvoudiginformatieobject",
            name="documenten_enkelvoudiginformatieobject__informatieobjecttype_base_url_and__informatieobjecttype_relative_url_filled",
        ),
        migrations.RenameField(
            model_name="enkelvoudiginformatieobject",
            old_name="_informatieobjecttype",
            new_name="informatieobjecttype",
        ),
        migrations.AlterField(
            model_name="enkelvoudiginformatieobject",
            name="informatieobjecttype",
            field=models.ForeignKey(
                to="catalogi.informatieobjecttype",
                on_delete=django.db.models.deletion.PROTECT,
                help_text="URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API).",
            ),
        ),
        migrations.RemoveField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_base_url",
        ),
        migrations.RemoveField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_relative_url",
        ),
        migrations.RemoveField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_url",
        ),
    ]
