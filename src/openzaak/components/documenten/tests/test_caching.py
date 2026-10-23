# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from uuid import uuid4

from django.db import connection
from django.test import tag
from django.test.utils import CaptureQueriesContext

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils import get_spec

from ..admin import unlock
from ..models import EnkelvoudigInformatieObjectCanonical, ObjectInformatieObject
from ..tests.factories import (
    BestandsDeelFactory,
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
)


@temp_private_root()
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

        etag = self.client.get(reverse(eio))["ETag"]

        response = self.client.get(reverse(eio), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        response = self.client.get(
            reverse(eio), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_new_bestandsdeel_invalidates_etag(self):
        """
        The bestandsdelen are read through the canonical, so adding one must
        invalidate the ETag.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        etag = self.client.get(reverse(eio))["ETag"]

        BestandsDeelFactory.create(informatieobject=eio.canonical)

        response = self.client.get(reverse(eio), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["bestandsdelen"]), 1)

    @tag("gh-2577")
    def test_admin_unlock_invalidates_etag(self):
        eio = EnkelvoudigInformatieObjectFactory.create(canonical__lock=uuid4().hex)
        etag = self.client.get(reverse(eio))["ETag"]

        unlock(
            None,
            None,
            EnkelvoudigInformatieObjectCanonical.objects.filter(pk=eio.canonical.pk),
        )

        response = self.client.get(reverse(eio), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["locked"])


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

        etag = self.client.get(reverse(oio))["ETag"]

        response = self.client.get(reverse(oio), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()

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

        etag = self.client.get(reverse(gebruiksrecht))["ETag"]

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": etag}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        response = self.client.get(
            reverse(gebruiksrecht), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag("gh-2577")
class GebruiksrechtenLockOrderTests(JWTAuthMixin, APITestCase):
    """
    Deleting the last gebruiksrecht of a document saves the document too. It must
    update the document before it writes stored ETags, as a lock or unlock of the
    document writes the document's and its gebruiksrechten's together; the other way
    round, the two deadlock.
    """

    heeft_alle_autorisaties = True

    def test_destroy(self):
        gebruiksrecht = GebruiksrechtenFactory.create()

        with CaptureQueriesContext(connection) as queries:
            response = self.client.delete(reverse(gebruiksrecht))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        sqls = [query["sql"] for query in queries]
        document_updates = [
            i
            for i, sql in enumerate(sqls)
            if sql.startswith('UPDATE "documenten_enkelvoudiginformatieobject"')
        ]
        etag_writes = [
            i
            for i, sql in enumerate(sqls)
            if sql.startswith(
                (
                    'INSERT INTO "vng_api_common_storedetag"',
                    'DELETE FROM "vng_api_common_storedetag"',
                )
            )
        ]
        self.assertTrue(document_updates)
        self.assertTrue(etag_writes)
        self.assertLess(document_updates[0], etag_writes[0])


@temp_private_root()
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

        etag = self.client.get(reverse(eio))["ETag"]

        eio.titel = "aangepast"
        eio.save()

        response = self.client.get(reverse(eio), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
