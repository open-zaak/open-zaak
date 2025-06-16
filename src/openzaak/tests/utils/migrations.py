# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, override_settings

unset = object()


class TestMigrations(TestCase):
    """
    Test the effect of applying a migration
    Copied from https://github.com/open-formulieren/open-forms/blob/master/src/openforms/utils/tests/test_migrations.py
    """

    app = None
    migrate_from = unset
    migrate_to = unset
    setting_overrides = None

    def setUp(self):
        _checks = (
            self.migrate_from is not unset,
            self.migrate_to is not unset,
            self.app,
        )
        assert all(_checks), (
            "TestCase '%s' must define migrate_from, migrate_to and app properties"
            % type(self).__name__
        )
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)

        # Reverse to the original migration
        old_migrate_state = executor.migrate(self.migrate_from)
        old_apps = old_migrate_state.apps

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        overrides = self.setting_overrides or {}
        with override_settings(**overrides):
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()  # reload.
            new_migrate_state = executor.migrate(self.migrate_to)

        self.apps = new_migrate_state.apps

    def setUpBeforeMigration(self, apps):
        pass
