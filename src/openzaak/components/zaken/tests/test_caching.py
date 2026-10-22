# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""

import time

from django.contrib.sites.models import Site
from django.db import connection, transaction
from django.test import tag
from django.test.utils import CaptureQueriesContext

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import get_spec

from ..models import ZaakInformatieObject
from .factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import ZAAK_READ_KWARGS, ZAAK_WRITE_KWARGS


class ZaakCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaak_get_cache_header(self):
        zaak = ZaakFactory.create()

        response = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)

        self.assertHasETag(response)

    def test_zaak_head_cache_header(self):
        zaak = ZaakFactory.create()

        self.assertHeadHasETag(reverse(zaak), **ZAAK_READ_KWARGS)

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/zaken/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaak = ZaakFactory.create()
        etag = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)["ETag"]

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH=etag, **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaak = ZaakFactory.create()

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH='"not-an-md5"', **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalidate_new_status(self):
        """
        Status URL is part of the resource, so new status invalidates the ETag.
        """
        zaak = ZaakFactory.create()
        etag = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)["ETag"]

        # reset the on_commit callbacks from the test setup
        conn = transaction.get_connection()
        conn.run_on_commit = []

        with self.captureOnCommitCallbacks(execute=True):
            # create new status
            StatusFactory.create(zaak=zaak)

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH=etag, **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @tag("gh-2577")
    def test_expand_gets_no_etag(self):
        """
        An expanded zaak is another representation than the one the ETag validates.
        """
        zaak = ZaakFactory.create()
        etag = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)["ETag"]

        response = self.client.get(
            reverse(zaak),
            {"expand": "zaaktype"},
            headers={"if-none-match": etag},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("ETag", response)

    @tag("gh-2577")
    def test_create_with_gerelateerde_zaak_invalidates_its_etag(self):
        """
        Creating a zaak adds the reverse relation to its gerelateerde zaak, in one
        batch of invalidations.
        """
        gerelateerde_zaak = ZaakFactory.create()
        etag = self.client.get(reverse(gerelateerde_zaak), **ZAAK_READ_KWARGS)["ETag"]
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.client.post(
            reverse("zaak-list"),
            {
                "zaaktype": f"http://testserver{reverse(zaaktype)}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "startdatum": "2018-06-11",
                "gerelateerdeZaken": [
                    {"url": f"http://testserver{reverse(gerelateerde_zaak)}"}
                ],
            },
            **ZAAK_WRITE_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.get(
            reverse(gerelateerde_zaak),
            headers={"if-none-match": etag},
            **ZAAK_READ_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["gerelateerdeZaken"]), 1)


class StatusCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_status_get_cache_header(self):
        status_ = StatusFactory.create()

        response = self.client.get(reverse(status_))

        self.assertHasETag(response)

    def test_status_head_cache_header(self):
        status_ = StatusFactory.create()

        self.assertHeadHasETag(reverse(status_))

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/statussen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        """
        Test that, if I have a cached copy, the API returns an HTTP 304.
        """
        status_ = StatusFactory.create()
        etag = self.client.get(reverse(status_))["ETag"]

        response = self.client.get(reverse(status_), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        status_ = StatusFactory.create()

        response = self.client.get(
            reverse(status_), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakInformatieObjectCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaakinformatieobject_get_cache_header(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create()

        response = self.client.get(reverse(zaakinformatieobject))

        self.assertHasETag(response)

    def test_zaakinformatieobject_head_cache_header(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(zaakinformatieobject))

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/zaakinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zio = ZaakInformatieObjectFactory.create()
        etag = self.client.get(reverse(zio))["ETag"]

        response = self.client.get(reverse(zio), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zio = ZaakInformatieObjectFactory.create()

        response = self.client.get(reverse(zio), headers={"if-none-match": '"old"'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag("gh-2577")
class ZaakInformatieObjectLockOrderTests(JWTAuthMixin, APITestCase):
    """
    A ZIO write saves its zaak too. It must update the zaak's row before it writes
    the zaak's stored ETag, as a save of the zaak does; the other way round, the two
    deadlock.
    """

    heeft_alle_autorisaties = True

    def assertZaakUpdatedBeforeStoredETags(self, queries):
        sqls = [query["sql"] for query in queries]
        zaak_updates = [
            i for i, sql in enumerate(sqls) if sql.startswith('UPDATE "zaken_zaak"')
        ]
        etag_writes = [
            i
            for i, sql in enumerate(sqls)
            if sql.startswith('INSERT INTO "vng_api_common_storedetag"')
        ]
        self.assertTrue(zaak_updates)
        self.assertTrue(etag_writes)
        self.assertLess(zaak_updates[0], etag_writes[0])

    def test_create(self):
        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(
                reverse(ZaakInformatieObject),
                {
                    "zaak": f"http://testserver{reverse(zaak)}",
                    "informatieobject": f"http://testserver{reverse(io)}",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertZaakUpdatedBeforeStoredETags(queries)

    def test_update(self):
        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create()
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak, informatieobject=io.canonical
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.patch(reverse(zio), {"titel": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertZaakUpdatedBeforeStoredETags(queries)

    def test_destroy(self):
        zio = ZaakInformatieObjectFactory.create()

        with CaptureQueriesContext(connection) as queries:
            response = self.client.delete(reverse(zio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertZaakUpdatedBeforeStoredETags(queries)


class ZaakEigenschapCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaakeigenschap_get_cache_header(self):
        zaakeigenschap = ZaakEigenschapFactory.create()

        response = self.client.get(
            reverse(zaakeigenschap, kwargs={"zaak_uuid": zaakeigenschap.zaak.uuid})
        )

        self.assertHasETag(response)

    def test_zaakeigenschap_head_cache_header(self):
        zaakeigenschap = ZaakEigenschapFactory.create()

        self.assertHeadHasETag(
            reverse(zaakeigenschap, kwargs={"zaak_uuid": zaakeigenschap.zaak.uuid})
        )

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/zaken/{zaak_uuid}/zaakeigenschappen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaak_eigenschap = ZaakEigenschapFactory.create()
        url = reverse(zaak_eigenschap, kwargs={"zaak_uuid": zaak_eigenschap.zaak.uuid})
        etag = self.client.get(url)["ETag"]

        response = self.client.get(
            url,
            headers={"if-none-match": etag},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaak_eigenschap = ZaakEigenschapFactory.create()

        response = self.client.get(
            reverse(zaak_eigenschap, kwargs={"zaak_uuid": zaak_eigenschap.zaak.uuid}),
            headers={"if-none-match": '"old"'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RolCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_rol_get_cache_header(self):
        rol = RolFactory.create()

        response = self.client.get(reverse(rol))

        self.assertHasETag(response)

    def test_rol_head_cache_header(self):
        rol = RolFactory.create()

        self.assertHeadHasETag(reverse(rol))

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/rollen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        rol = RolFactory.create()
        etag = self.client.get(reverse(rol))["ETag"]

        response = self.client.get(reverse(rol), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        rol = RolFactory.create()

        response = self.client.get(reverse(rol), headers={"if-none-match": '"old"'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResultaatCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_resultaat_get_cache_header(self):
        resultaat = ResultaatFactory.create()

        response = self.client.get(reverse(resultaat))

        self.assertHasETag(response)

    def test_resultaat_head_cache_header(self):
        resultaat = ResultaatFactory.create()

        self.assertHeadHasETag(reverse(resultaat))

    def test_head_in_apischema(self):
        spec = get_spec("zaken")

        endpoint = spec["paths"]["/resultaten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        resultaat = ResultaatFactory.create()
        etag = self.client.get(reverse(resultaat))["ETag"]

        response = self.client.get(reverse(resultaat), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        resultaat = ResultaatFactory.create()

        response = self.client.get(
            reverse(resultaat), headers={"if-none-match": '"old"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag("gh-2577")
@temp_private_root()
class ZaakInformatieObjectCostTests(JWTAuthMixin, APITestCase):
    """
    The queries of adding a ZIO, and of the first GET of the zaak after it, must not
    grow with the number of ZIOs the zaak already has.

    The POST only invalidates the zaak's ETag; the GET calculates it.
    """

    heeft_alle_autorisaties = True

    @staticmethod
    def _create_zios(zaak, amount: int) -> None:
        """
        Link ``amount`` documents to the zaak, without the factory's file per document.

        The documents share one informatieobjecttype and one file, which is enough
        for the (zaak, informatieobject) pairs to be distinct and valid.
        """
        template = EnkelvoudigInformatieObjectFactory.create()
        canonicals = EnkelvoudigInformatieObjectCanonical.objects.bulk_create(
            [EnkelvoudigInformatieObjectCanonical() for _ in range(amount)]
        )
        versions = EnkelvoudigInformatieObject.objects.bulk_create(
            [
                EnkelvoudigInformatieObject(
                    canonical=canonical,
                    identificatie=f"{template.identificatie}-{n}",
                    bronorganisatie=template.bronorganisatie,
                    creatiedatum=template.creatiedatum,
                    titel=template.titel,
                    auteur=template.auteur,
                    formaat=template.formaat,
                    taal=template.taal,
                    inhoud=template.inhoud.name,
                    bestandsomvang=template.bestandsomvang,
                    informatieobjecttype=template.informatieobjecttype,
                    vertrouwelijkheidaanduiding=template.vertrouwelijkheidaanduiding,
                )
                for n, canonical in enumerate(canonicals)
            ]
        )
        for version in versions:
            version.canonical.latest_version = version
        EnkelvoudigInformatieObjectCanonical.objects.bulk_update(
            canonicals, ["latest_version"]
        )
        for canonical in canonicals:
            ZaakInformatieObject.objects.create(zaak=zaak, _informatieobject=canonical)

    def _measure(self, existing: int) -> tuple[int, int, float, float]:
        zaak = ZaakFactory.create()
        self._create_zios(zaak, existing)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        data = {
            "informatieobject": f"http://testserver{reverse(io)}",
            "zaak": f"http://testserver{reverse(zaak)}",
        }
        url = reverse_lazy(ZaakInformatieObject)
        # the first request of the test would otherwise be the only one to query it
        Site.objects.clear_cache()

        with CaptureQueriesContext(connection) as post_queries:
            start = time.perf_counter()
            response = self.client.post(url, data)
            post_duration = time.perf_counter() - start
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        with CaptureQueriesContext(connection) as get_queries:
            start = time.perf_counter()
            response = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)
            get_duration = time.perf_counter() - start
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("ETag", response)

        return len(post_queries), len(get_queries), post_duration, get_duration

    def test_cost_does_not_grow_with_existing_zios(self):
        *with_one, post_one, get_one = self._measure(1)
        *with_many, post_many, get_many = self._measure(500)

        self.assertEqual(with_many, with_one)
        # Wall-clock time is flaky, so only a generous bound, with slack for a stall on
        # CI: the POST should cost the same; the GET lists 500 URLs, so it may be
        # somewhat slower.
        self.assertLess(
            post_many, 10 * post_one + 0.5, f"{post_one=:.3f}s {post_many=:.3f}s"
        )
        self.assertLess(
            get_many, 10 * get_one + 0.5, f"{get_one=:.3f}s {get_many=:.3f}s"
        )
