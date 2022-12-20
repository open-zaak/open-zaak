# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Open Zaak maintainers
import zlib
from contextlib import contextmanager

from django.db import connections, transaction


@contextmanager
def pg_advisory_lock(lock_id: str, using="default"):
    _lock_id = zlib.crc32(lock_id.encode("utf-8"))
    with transaction.atomic(using=using):
        connection = connections[using]
        with connection.cursor() as cursor:
            sql = f"SELECT pg_advisory_xact_lock({_lock_id})"
            cursor.execute(sql)
            yield
