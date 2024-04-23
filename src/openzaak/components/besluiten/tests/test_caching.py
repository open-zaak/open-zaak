# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.tests.utils import get_spec

from .factories import BesluitFactory, BesluitInformatieObjectFactory


class BesluitCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluit_get_cache_header(self):
        besluit = BesluitFactory.create()

        response = self.client.get(reverse(besluit))

        self.assertHasETag(response)

    def test_besluit_head_cache_header(self):
        besluit = BesluitFactory.create()

        self.assertHeadHasETag(reverse(besluit))

    def test_head_in_apischema(self):
        spec = get_spec("besluiten")

        endpoint = spec["paths"]["/besluiten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        besluit = BesluitFactory.create(with_etag=True)

        response = self.client.get(
            reverse(besluit), headers={"if-none-match": f'"{besluit._etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        besluit = BesluitFactory.create(with_etag=True)

        response = self.client.get(
            reverse(besluit), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BesluitInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluitinformatieobject_get_cache_header(self):
        besluitinformatieobject = BesluitInformatieObjectFactory.create()

        response = self.client.get(reverse(besluitinformatieobject))

        self.assertHasETag(response)

    def test_besluitinformatieobject_head_cache_header(self):
        besluitinformatieobject = BesluitInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(besluitinformatieobject))

    def test_head_in_apischema(self):
        spec = get_spec("besluiten")

        endpoint = spec["paths"]["/besluitinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(
            reverse(bio), headers={"if-none-match": f'"{bio._etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(reverse(bio), headers={"if-none-match": '"old"'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
