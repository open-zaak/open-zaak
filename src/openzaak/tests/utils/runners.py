# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.core.checks.registry import registry
from django.test.runner import DiscoverRunner


class CITestRunner(DiscoverRunner):
    def run_checks(self, databases):
        from zgw_consumers.checks import check_zgw_auth_secret

        # This database check is causing issues with DB_POOL_ENABLED when running tests
        # in parallel. Ideally I'd get rid of DB pooling via django entirely because it
        # didn't prove to be of any use. But that's something for a major version bump
        registry.registered_checks.discard(check_zgw_auth_secret)
        super().run_checks(databases)
