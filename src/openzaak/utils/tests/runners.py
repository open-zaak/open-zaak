# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import multiprocessing

from django.test.runner import DiscoverRunner


class ForkTestRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        multiprocessing.set_start_method("fork", force=True)
        super().__init__(*args, **kwargs)
