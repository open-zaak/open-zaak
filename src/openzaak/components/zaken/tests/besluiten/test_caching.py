# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.tests.utils import get_spec
from openzaak.utils.urls import reverse


class BesluitCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluit_get_cache_header(self):
        besluit = BesluitFactory.create()

        response = self.client.get(reverse(besluit, namespace="zaken"))

        self.assertHasETag(response)

    def test_besluit_head_cache_header(self):
        besluit = BesluitFactory.create()

        self.assertHeadHasETag(reverse(besluit, namespace="zaken"))

    def test_head_in_apischema(self):
        spec = get_spec("besluiten")

        endpoint = spec["paths"]["/besluiten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        besluit = BesluitFactory.create(with_etag=True)

        response = self.client.get(
            reverse(besluit, namespace="zaken"),
            headers={"if-none-match": f'"{besluit._etag}"'},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        besluit = BesluitFactory.create(with_etag=True)

        response = self.client.get(
            reverse(besluit, namespace="zaken"),
            headers={"if-none-match": '"not-an-md5"'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BesluitInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluitinformatieobject_get_cache_header(self):
        besluitinformatieobject = BesluitInformatieObjectFactory.create()

        response = self.client.get(reverse(besluitinformatieobject, namespace="zaken"))

        self.assertHasETag(response)

    def test_besluitinformatieobject_head_cache_header(self):
        besluitinformatieobject = BesluitInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(besluitinformatieobject, namespace="zaken"))

    def test_head_in_apischema(self):
        spec = get_spec("besluiten")

        endpoint = spec["paths"]["/besluitinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(
            reverse(bio, namespace="zaken"), headers={"if-none-match": f'"{bio._etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(
            reverse(bio, namespace="zaken"), headers={"if-none-match": '"old"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
