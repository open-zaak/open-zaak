# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Open Zaak maintainers
import threading
import time

from django.test import TransactionTestCase

from openzaak.utils.db import pg_advisory_lock


class AdvisoryLockTests(TransactionTestCase):
    def test_advisory_lock_blocks_and_waits(self):
        shared_list = []

        def worker(wait_before: float, item: str, wait_during: float):
            time.sleep(wait_before)
            with pg_advisory_lock(
                "AdvisoryLockTests.test_advisory_lock_blocks_and_waits"
            ):
                time.sleep(wait_during)
                shared_list.append(item)

        # timeline:
        #
        #  0.00: t1 starts
        #  0.00: t2 starts
        #  0.01: t2 wakes and acquires the lock and starts sleep for 0.2s
        #  0.10: t1 wakes and waits to acquire lock
        #  0.21: t2 wakes and inserts 'second' into the list
        # ~0.21: t2 releases lock
        # ~0.21: t1 acquires lock and sleeps for 0.0s
        # ~0.21: t1 wakes and inserts 'first' into the list
        #
        #  If the lock would not be exclusive, then t1 would insert after about 0.10s
        #  while t2 would still only insert after about ~0.21s, which would make the
        #  order of items in the list ['first', 'second']
        t1 = threading.Thread(target=worker, args=(0.10, "first", 0.0))
        t2 = threading.Thread(target=worker, args=(0.01, "second", 0.2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(shared_list, ["second", "first"])
