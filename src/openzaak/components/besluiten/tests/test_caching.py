# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)

from .utils import get_besluiten_spec


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
        spec = get_besluiten_spec()

        endpoint = spec["paths"]["/besluiten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        besluit = BesluitFactory.create(with_etag=True, ingangsdatum="2020-01-01")
        response = self.client.get(
            reverse(besluit), HTTP_IF_NONE_MATCH=f'"{besluit._etag}"'
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        besluit = BesluitFactory.create(with_etag=True, ingangsdatum="2020-01-01")

        response = self.client.get(reverse(besluit), HTTP_IF_NONE_MATCH='"not-an-md5"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BesluitInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluit_get_cache_header(self):
        bio = BesluitInformatieObjectFactory.create()

        response = self.client.get(reverse(bio))

        self.assertHasETag(response)

    def test_besluit_head_cache_header(self):
        bio = BesluitInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(bio))

    def test_head_in_apischema(self):
        spec = get_besluiten_spec()

        endpoint = spec["paths"]["/besluitinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)
        response = self.client.get(reverse(bio), HTTP_IF_NONE_MATCH=f'"{bio._etag}"')

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        bio = BesluitInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(reverse(bio), HTTP_IF_NONE_MATCH='"not-an-md5"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BesluitCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self._create_credentials(
            self.client_id,
            self.secret,
            self.heeft_alle_autorisaties,
            self.max_vertrouwelijkheidaanduiding,
        )

    def test_invalidate_etag_after_change(self):
        """
        Because changes are made to the besluit, a code 200 should be returned
        """
        besluit = BesluitFactory.create(
            toelichting="", with_etag=True, ingangsdatum="2020-01-01"
        )
        etag = besluit._etag

        besluit.toelichting = "bla"
        besluit.save()

        response = self.client.get(reverse(besluit), HTTP_IF_NONE_MATCH=f"{etag}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
