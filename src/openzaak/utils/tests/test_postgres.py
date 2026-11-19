# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from django.db import connection
from django.test import TestCase


class PostgreSQLVersionTest(TestCase):
    def test_postgres_version(self):
        version = connection.pg_version  # pyright: ignore[reportAttributeAccessIssue]
        current_version = version // 10000
        min_supported_version = 15
        max_supported_version = 18
        assert min_supported_version <= current_version <= max_supported_version, (
            f"PostgreSQL version must be between {min_supported_version} and"
            "{max_supported_version}, but got {current_version}"
        )
