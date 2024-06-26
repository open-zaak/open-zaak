# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
# Generated by Django 4.2.11 on 2024-04-23 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documenten", "0031_enkelvoudiginformatieobject_trefwoorden"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="enkelvoudiginformatieobject",
            name="documenten_enkelvoudiginformatieobject__informatieobjecttype_base_url_and__informatieobjecttype_relative_url_filled",
        ),
        migrations.RemoveConstraint(
            model_name="objectinformatieobject",
            name="documenten_objectinformatieobject__object_base_url_and__object_relative_url_filled",
        ),
        migrations.AddConstraint(
            model_name="enkelvoudiginformatieobject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("_informatieobjecttype_base_url__isnull", True),
                        models.Q(
                            ("_informatieobjecttype_relative_url__isnull", True),
                            ("_informatieobjecttype_relative_url", ""),
                            _connector="OR",
                        ),
                    ),
                    models.Q(
                        models.Q(
                            ("_informatieobjecttype_base_url__isnull", True),
                            _negated=True,
                        ),
                        models.Q(
                            ("_informatieobjecttype_relative_url__isnull", True),
                            ("_informatieobjecttype_relative_url", ""),
                            _connector="OR",
                            _negated=True,
                        ),
                    ),
                    _connector="OR",
                ),
                name="documenten_enkelvoudiginformatieobject__informatieobjecttype_base_url_and__informatieobjecttype_relative_url_filled",
            ),
        ),
        migrations.AddConstraint(
            model_name="objectinformatieobject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("_object_base_url__isnull", True),
                        models.Q(
                            ("_object_relative_url__isnull", True),
                            ("_object_relative_url", ""),
                            _connector="OR",
                        ),
                    ),
                    models.Q(
                        models.Q(("_object_base_url__isnull", True), _negated=True),
                        models.Q(
                            ("_object_relative_url__isnull", True),
                            ("_object_relative_url", ""),
                            _connector="OR",
                            _negated=True,
                        ),
                    ),
                    _connector="OR",
                ),
                name="documenten_objectinformatieobject__object_base_url_and__object_relative_url_filled",
            ),
        ),
    ]
