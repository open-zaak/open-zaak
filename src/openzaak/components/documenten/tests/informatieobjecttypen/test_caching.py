# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.caching import calculate_etag
from vng_api_common.tests import CacheMixin, JWTAuthMixin

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
)
from openzaak.tests.utils import get_spec
from openzaak.utils.urls import reverse


class InformatieObjectTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_informatieobjecttype_get_cache_header(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        response = self.client.get(reverse(informatieobjecttype))

        self.assertHasETag(response)

    def test_informatieobjecttype_head_cache_header(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        self.assertHeadHasETag(reverse(informatieobjecttype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/informatieobjecttypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(with_etag=True)
        response = self.client.get(
            reverse(informatieobjecttype),
            headers={"if-none-match": f'"{informatieobjecttype._etag}"'},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(with_etag=True)

        response = self.client.get(
            reverse(informatieobjecttype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InformatieObjectTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the informatieobjecttype, a code 200 should be
        returned
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(
            omschrijving="bla", with_etag=True
        )
        informatieobjecttype._etag = calculate_etag(informatieobjecttype)
        informatieobjecttype.save(update_fields=["_etag"])
        etag = informatieobjecttype._etag

        informatieobjecttype.omschrijving = "same"
        informatieobjecttype.save()

        response = self.client.get(
            reverse(informatieobjecttype), headers={"if-none-match": f'"{etag}"'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the informatieobjecttype, a code 304 should be
        returned
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(omschrijving="bla")
        informatieobjecttype._etag = calculate_etag(informatieobjecttype)
        informatieobjecttype.save(update_fields=["_etag"])
        etag = informatieobjecttype._etag

        response = self.client.get(
            reverse(informatieobjecttype), headers={"if-none-match": f'"{etag}"'}
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)
