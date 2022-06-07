# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.test import TestCase

from openzaak.utils.cache import DjangoCacheStorage


class DjangoCacheStorageTestCase(TestCase):
    """
    Test basic operations for the custom request-cache backend, based on the Django
    cache framework
    """

    def setUp(self):
        super().setUp()
        self.storage = DjangoCacheStorage(cache_name="import_requests")

    def test_setitem(self):
        self.storage["foo"] = "bar"

        self.assertEqual(self.storage.cache.get("foo"), "bar")

    def test_getitem(self):
        self.storage.cache.set("foo", "bar")

        self.assertEqual(self.storage["foo"], "bar")

    def test_contains(self):
        self.storage.cache.set("foo", "bar")

        self.assertTrue("foo" in self.storage)

    def test_delete(self):
        self.storage.cache.set("foo", "bar")
        del self.storage["foo"]

        self.assertFalse("foo" in self.storage.cache)

    def test_bulk_delete(self):
        self.storage.cache.set("foo", "bar")
        self.storage.cache.set("bar", "foo")
        self.storage.bulk_delete(["foo", "bar"])

        self.assertFalse("foo" in self.storage.cache)
        self.assertFalse("bar" in self.storage.cache)

    def test_clear(self):
        self.storage.cache.set("foo", "bar")
        self.storage.cache.set("bar", "foo")

        self.storage.clear()

        self.assertFalse("foo" in self.storage)
        self.assertFalse("bar" in self.storage)
