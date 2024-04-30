# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils import get_spec

from ..caching import get_etag_cache_key, set_etag
from ..models import ObjectInformatieObject
from ..tests.factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory


class EnkelvoudigInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_eio_get_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        response = self.client.get(reverse(eio))

        self.assertHasETag(response)

    def test_eio_head_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(eio))

    def test_head_in_apischema(self):
        spec = get_spec("documenten")

        endpoint = spec["paths"]["/enkelvoudiginformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        key = get_etag_cache_key(eio)
        _etag = eio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(eio), headers={"if-none-match": f'"{_etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        response = self.client.get(
            reverse(eio), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ObjectInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_oio_get_cache_header(self):
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()

        response = self.client.get(reverse(oio))

        self.assertHasETag(response)

    def test_oio_head_cache_header(self):
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()

        self.assertHeadHasETag(reverse(oio))

    def test_head_in_apischema(self):
        spec = get_spec("documenten")

        endpoint = spec["paths"]["/objectinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()

        # Manually set the ETag, since there is no OIO factory
        key = get_etag_cache_key(oio)
        _etag = oio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(oio), headers={"if-none-match": f'"{_etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()

        # Manually set the ETag, since there is no OIO factory
        key = get_etag_cache_key(oio)
        _etag = oio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(oio), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GebruiksrechtenCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_gebruiksrecht_get_cache_header(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        response = self.client.get(reverse(gebruiksrecht))

        self.assertHasETag(response)

    def test_gebruiksrechthead_cache_header(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        self.assertHeadHasETag(reverse(gebruiksrecht))

    def test_head_in_apischema(self):
        spec = get_spec("documenten")

        endpoint = spec["paths"]["/gebruiksrechten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        key = get_etag_cache_key(gebruiksrecht)
        _etag = gebruiksrecht.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": f'"{_etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        key = get_etag_cache_key(gebruiksrecht)
        _etag = gebruiksrecht.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EnkelvoudigInformatieObjectCacheTransactionTests(
    JWTAuthMixin, APITransactionTestCase
):
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
        Because changes are made to the informatieobject, a code 200 should be
        returned
        """
        eio = EnkelvoudigInformatieObjectFactory.create(titel="bla")

        key = get_etag_cache_key(eio)
        _etag = eio.calculate_etag_value()
        set_etag(key, _etag)

        eio.titel = "aangepast"
        eio.save()

        response = self.client.get(reverse(eio), headers={"if-none-match": f"{_etag}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
