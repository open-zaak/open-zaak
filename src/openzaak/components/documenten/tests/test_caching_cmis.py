# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenCMISFactory,
)
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory

from ..caching import get_etag, get_etag_cache_key, set_etag
from .utils import get_documenten_spec


@override_settings(CMIS_ENABLED=True)
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
        spec = get_documenten_spec()

        endpoint = spec["paths"]["/enkelvoudiginformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create(with_etag=True)
        _etag = get_etag(get_etag_cache_key(eio))

        response = self.client.get(reverse(eio), HTTP_IF_NONE_MATCH=f'"{_etag}"')

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(reverse(eio), HTTP_IF_NONE_MATCH='"not-an-md5"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(CMIS_ENABLED=True)
class ObjectInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_oio_get_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        response = self.client.get(reverse(oio))

        self.assertHasETag(response)

    def test_oio_head_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        # relate the two
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        self.assertHeadHasETag(reverse(oio))

    def test_head_in_apischema(self):
        spec = get_documenten_spec()

        endpoint = spec["paths"]["/objectinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        # Manually set the ETag, since there is no OIO factory
        _etag = oio.calculate_etag_value()
        set_etag(get_etag_cache_key(oio), _etag)

        response = self.client.get(reverse(oio), HTTP_IF_NONE_MATCH=f'"{_etag}"')

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        # Manually set the ETag, since there is no OIO factory
        set_etag(get_etag_cache_key(oio), oio.calculate_etag_value())

        response = self.client.get(reverse(oio), HTTP_IF_NONE_MATCH='"not-an-md5"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_gebruiksrecht_get_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        response = self.client.get(reverse(gebruiksrecht))

        self.assertHasETag(response)

    def test_gebruiksrechthead_cache_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        self.assertHeadHasETag(reverse(gebruiksrecht))

    def test_head_in_apischema(self):
        spec = get_documenten_spec()

        endpoint = spec["paths"]["/gebruiksrechten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(
            with_etag=True, informatieobject=eio_url
        )

        _etag = get_etag(get_etag_cache_key(gebruiksrecht))

        response = self.client.get(
            reverse(gebruiksrecht), HTTP_IF_NONE_MATCH=f'"{_etag}"'
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(
            informatieobject=eio_url, with_etag=True
        )

        response = self.client.get(
            reverse(gebruiksrecht), HTTP_IF_NONE_MATCH='"not-an-md5"'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(CMIS_ENABLED=True)
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
        eio = EnkelvoudigInformatieObjectFactory.create(titel="bla", with_etag=True)
        etag = eio._etag

        eio.titel = "aangepast"
        eio.save()

        response = self.client.get(reverse(eio), HTTP_IF_NONE_MATCH=f"{etag}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
