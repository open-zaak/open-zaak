# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("admin_index", "0002_auto_20170802_1754"),
        ("besluiten", "0001_initial"),
        ("catalogi", "0001_initial"),
        ("documenten", "0001_initial"),
        ("notifications", "0009_auto_20190729_0427"),
        ("zaken", "0001_initial"),
    ]

    operations = []
