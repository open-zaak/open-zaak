# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.tests.utils import JWTAuthMixin, get_spec

from ..constants import VervalRedenen
from ..models import Besluit
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


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class BesluitCreateTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_besluit_cachalot(self):
        """
        Assert that the zaak list cache is invalidated when a new Zaak is created
        """
        url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        BesluitFactory.create()

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # re-request list
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
