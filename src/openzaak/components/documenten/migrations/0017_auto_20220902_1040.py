# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.15 on 2022-09-02 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documenten", "0016_move_url_field_contents"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="objectinformatieobject", name="check_type",
        ),
        migrations.RemoveConstraint(
            model_name="objectinformatieobject", name="unique_io_zaak_external",
        ),
        migrations.RemoveConstraint(
            model_name="objectinformatieobject", name="unique_io_besluit_external",
        ),
        migrations.RemoveField(
            model_name="objectinformatieobject", name="_besluit_url",
        ),
        migrations.RemoveField(model_name="objectinformatieobject", name="_zaak_url",),
        migrations.AddConstraint(
            model_name="objectinformatieobject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("_besluit__isnull", True),
                        ("_object_url", ""),
                        ("_zaak__isnull", False),
                    ),
                    models.Q(
                        ("_besluit__isnull", False),
                        ("_object_url", ""),
                        ("_zaak__isnull", True),
                    ),
                    models.Q(
                        models.Q(("_object_url", ""), _negated=True),
                        ("_besluit__isnull", True),
                        ("_zaak__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="object_reference_fields_mutex",
            ),
        ),
        migrations.AddConstraint(
            model_name="objectinformatieobject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(
                            ("_zaak__isnull", False),
                            models.Q(("_object_url", ""), _negated=True),
                            _connector="OR",
                        ),
                        ("object_type", "zaak"),
                    ),
                    models.Q(
                        models.Q(
                            ("_besluit__isnull", False),
                            models.Q(("_object_url", ""), _negated=True),
                            _connector="OR",
                        ),
                        ("object_type", "besluit"),
                    ),
                    models.Q(
                        models.Q(("_object_url", ""), _negated=True),
                        ("object_type", "verzoek"),
                    ),
                    _connector="OR",
                ),
                name="correct_field_set_for_object_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="objectinformatieobject",
            constraint=models.UniqueConstraint(
                condition=models.Q(("_object_url", ""), _negated=True),
                fields=("informatieobject", "_object_url"),
                name="unique_io_object_external",
            ),
        ),
    ]