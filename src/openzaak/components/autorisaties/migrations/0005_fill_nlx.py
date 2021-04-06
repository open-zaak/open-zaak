# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("autorisaties", "0004_delete_externalapicredential"),
        ("zgw_consumers", "0008_auto_20200331_1400"),
    ]

    # this used to migrate nlx-url-rewriter entries to zgw-consumers, but the dependency
    # has been dropped
    operations = []
