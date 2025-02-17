# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""
from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils import APICMISTestCase, get_spec, require_cmis

from ..caching import get_etag_cache_key, set_etag
from ..models import ObjectInformatieObject
from ..tests.factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenCMISFactory,
)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class EnkelvoudigInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APICMISTestCase):
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

        key = get_etag_cache_key(eio)
        _etag = eio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(eio), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class ObjectInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APICMISTestCase):
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
        spec = get_spec("documenten")

        endpoint = spec["paths"]["/objectinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        # Manually set the ETag, since there is no OIO factory
        key = get_etag_cache_key(oio)
        _etag = eio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(oio), headers={"if-none-match": f'"{_etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get(informatieobject=eio_url)

        # Manually set the ETag, since there is no OIO factory
        key = get_etag_cache_key(oio)
        _etag = oio.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(oio), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenCacheTests(CacheMixin, JWTAuthMixin, APICMISTestCase):
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
        spec = get_spec("documenten")

        endpoint = spec["paths"]["/gebruiksrechten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        key = get_etag_cache_key(gebruiksrecht)
        _etag = gebruiksrecht.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": f'"{_etag}"'}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrecht = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        key = get_etag_cache_key(gebruiksrecht)
        _etag = gebruiksrecht.calculate_etag_value()
        set_etag(key, _etag)

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class EnkelvoudigInformatieObjectCacheTransactionTests(JWTAuthMixin, APICMISTestCase):
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
        ServiceFactory.create(api_root="http://testserver/", api_type=APITypes.orc)
        eio = EnkelvoudigInformatieObjectFactory.create(titel="bla")

        key = get_etag_cache_key(eio)
        _etag = eio.calculate_etag_value()
        set_etag(key, _etag)

        eio.titel = "aangepast"
        eio.save()

        response = self.client.get(reverse(eio), headers={"if-none-match": f"{_etag}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
