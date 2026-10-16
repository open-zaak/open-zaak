# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from types import SimpleNamespace

from django.contrib import admin
from django.test import RequestFactory, tag

from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.admin.zaaktypen import ZaakTypeAdmin
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.tests.utils import get_spec


class BesluitTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluittype_get_cache_header(self):
        besluittype = BesluitTypeFactory.create()

        response = self.client.get(reverse(besluittype))

        self.assertHasETag(response)

    def test_besluittype_head_cache_header(self):
        besluittype = BesluitTypeFactory.create()

        self.assertHeadHasETag(reverse(besluittype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/besluittypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        besluittype = BesluitTypeFactory.create()
        etag = self.client.get(reverse(besluittype))["ETag"]
        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": etag}
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        besluittype = BesluitTypeFactory.create()

        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BesluitTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the besluittype, a code 200 should be
        returned
        """
        besluittype = BesluitTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(besluittype))["ETag"]

        besluittype.omschrijving = "same"
        besluittype.save()

        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the besluittype, a code 304 should be
        returned
        """
        besluittype = BesluitTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(besluittype))["ETag"]

        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class CatalogusCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_catalogus_get_cache_header(self):
        catalogus = CatalogusFactory.create()

        response = self.client.get(reverse(catalogus))

        self.assertHasETag(response)

    def test_catalogus_head_cache_header(self):
        catalogus = CatalogusFactory.create()

        self.assertHeadHasETag(reverse(catalogus))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/catalogussen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        catalogus = CatalogusFactory.create()
        etag = self.client.get(reverse(catalogus))["ETag"]
        response = self.client.get(reverse(catalogus), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        catalogus = CatalogusFactory.create()

        response = self.client.get(
            reverse(catalogus), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CatalogusCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the catalogus, a code 200 should be
        returned
        """
        catalogus = CatalogusFactory.create(domein="bla")
        etag = self.client.get(reverse(catalogus))["ETag"]

        catalogus.domein = "same"
        catalogus.save()

        response = self.client.get(reverse(catalogus), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the catalogus, a code 304 should be
        returned
        """
        catalogus = CatalogusFactory.create(domein="bla")
        etag = self.client.get(reverse(catalogus))["ETag"]

        response = self.client.get(reverse(catalogus), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class EigenschapCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_eigenschap_get_cache_header(self):
        eigenschap = EigenschapFactory.create()

        response = self.client.get(reverse(eigenschap))

        self.assertHasETag(response)

    def test_eigenschap_head_cache_header(self):
        eigenschap = EigenschapFactory.create()

        self.assertHeadHasETag(reverse(eigenschap))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/eigenschappen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        eigenschap = EigenschapFactory.create()
        etag = self.client.get(reverse(eigenschap))["ETag"]
        response = self.client.get(reverse(eigenschap), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        eigenschap = EigenschapFactory.create()

        response = self.client.get(
            reverse(eigenschap), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EigenschapCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the eigenschap, a code 200 should be
        returned
        """
        eigenschap = EigenschapFactory.create(toelichting="bla")
        etag = self.client.get(reverse(eigenschap))["ETag"]

        eigenschap.toelichting = "same"
        eigenschap.save()

        response = self.client.get(reverse(eigenschap), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the eigenschap, a code 304 should be
        returned
        """
        eigenschap = EigenschapFactory.create(toelichting="bla")
        etag = self.client.get(reverse(eigenschap))["ETag"]

        response = self.client.get(reverse(eigenschap), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


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
        informatieobjecttype = InformatieObjectTypeFactory.create()
        etag = self.client.get(reverse(informatieobjecttype))["ETag"]
        response = self.client.get(
            reverse(informatieobjecttype),
            headers={"if-none-match": etag},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

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
            omschrijving="bla",
        )
        etag = self.client.get(reverse(informatieobjecttype))["ETag"]

        informatieobjecttype.omschrijving = "same"
        informatieobjecttype.save()

        response = self.client.get(
            reverse(informatieobjecttype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the informatieobjecttype, a code 304 should be
        returned
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(informatieobjecttype))["ETag"]

        response = self.client.get(
            reverse(informatieobjecttype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class ResultaatTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_resultaattype_get_cache_header(self):
        resultaattype = ResultaatTypeFactory.create(resultaattypeomschrijving="")

        response = self.client.get(reverse(resultaattype))

        self.assertHasETag(response)

    def test_resultaattype_head_cache_header(self):
        resultaattype = ResultaatTypeFactory.create(resultaattypeomschrijving="")

        self.assertHeadHasETag(reverse(resultaattype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/resultaattypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        resultaattype = ResultaatTypeFactory.create()
        etag = self.client.get(reverse(resultaattype))["ETag"]
        response = self.client.get(
            reverse(resultaattype),
            headers={"if-none-match": etag},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        resultaattype = ResultaatTypeFactory.create()

        response = self.client.get(
            reverse(resultaattype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @tag("gh-2577")
    def test_admin_selectielijst_reset_invalidates_etag(self):
        resultaattype = ResultaatTypeFactory.create(
            selectielijstklasse=(
                "https://selectielijst.openzaak.nl/api/v1/"
                "resultaten/65a0a7ab-0906-49bd-924f-f261f990b50f"
            )
        )
        etag = self.client.get(reverse(resultaattype))["ETag"]
        request = RequestFactory().post("/")
        request.user = SuperUserFactory.create()

        ZaakTypeAdmin(ZaakType, admin.site).save_model(
            request,
            resultaattype.zaaktype,
            SimpleNamespace(cleaned_data={"selectielijst_reset": True}),
            change=True,
        )

        response = self.client.get(
            reverse(resultaattype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["selectielijstklasse"], "")


class ResultaatTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the resultaattype, a code 200 should be
        returned
        """
        resultaattype = ResultaatTypeFactory.create(
            resultaattypeomschrijving="",
            omschrijving="bla",
        )
        etag = self.client.get(reverse(resultaattype))["ETag"]

        resultaattype.omschrijving = "same"
        resultaattype.save()

        response = self.client.get(
            reverse(resultaattype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the resultaattype, a code 304 should be
        returned
        """
        resultaattype = ResultaatTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(resultaattype))["ETag"]

        response = self.client.get(
            reverse(resultaattype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class RolTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_roltype_get_cache_header(self):
        roltype = RolTypeFactory.create()

        response = self.client.get(reverse(roltype))

        self.assertHasETag(response)

    def test_roltype_head_cache_header(self):
        roltype = RolTypeFactory.create()

        self.assertHeadHasETag(reverse(roltype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/roltypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        roltype = RolTypeFactory.create()
        etag = self.client.get(reverse(roltype))["ETag"]
        response = self.client.get(reverse(roltype), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        roltype = RolTypeFactory.create()

        response = self.client.get(
            reverse(roltype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RolTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the roltype, a code 200 should be
        returned
        """
        roltype = RolTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(roltype))["ETag"]

        roltype.omschrijving = "same"
        roltype.save()

        response = self.client.get(reverse(roltype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the roltype, a code 304 should be
        returned
        """
        roltype = RolTypeFactory.create(omschrijving="bla")
        etag = self.client.get(reverse(roltype))["ETag"]

        response = self.client.get(reverse(roltype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class StatusTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_statustype_get_cache_header(self):
        statustype = StatusTypeFactory.create()

        response = self.client.get(reverse(statustype))

        self.assertHasETag(response)

    def test_statustype_head_cache_header(self):
        statustype = StatusTypeFactory.create()

        self.assertHeadHasETag(reverse(statustype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/statustypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        statustype = StatusTypeFactory.create()
        etag = self.client.get(reverse(statustype))["ETag"]
        response = self.client.get(reverse(statustype), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        statustype = StatusTypeFactory.create()

        response = self.client.get(
            reverse(statustype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StatusTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the statustype, a code 200 should be
        returned
        """
        statustype = StatusTypeFactory.create(statustekst="bla")
        etag = self.client.get(reverse(statustype))["ETag"]

        statustype.statustekst = "same"
        statustype.save()

        response = self.client.get(reverse(statustype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the statustype, a code 304 should be
        returned
        """
        statustype = StatusTypeFactory.create(statustekst="bla")
        etag = self.client.get(reverse(statustype))["ETag"]

        response = self.client.get(reverse(statustype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class ZaakInformatieobjectTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaakinformatieobjecttype_get_cache_header(self):
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create()

        response = self.client.get(reverse(zaakinformatieobjecttype))

        self.assertHasETag(response)

    def test_zaakinformatieobjecttype_head_cache_header(self):
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create()

        self.assertHeadHasETag(reverse(zaakinformatieobjecttype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/zaaktype-informatieobjecttypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create()
        etag = self.client.get(reverse(zaakinformatieobjecttype))["ETag"]
        response = self.client.get(
            reverse(zaakinformatieobjecttype),
            headers={"if-none-match": etag},
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create()

        response = self.client.get(
            reverse(zaakinformatieobjecttype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakInformatieobjectTypeCacheTransactionTests(
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
        Because changes are made to the zaakinformatieobjecttype, a code 200 should be
        returned
        """
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create(
            volgnummer=1,
        )
        etag = self.client.get(reverse(zaakinformatieobjecttype))["ETag"]

        zaakinformatieobjecttype.volgnummer = 2
        zaakinformatieobjecttype.save()

        response = self.client.get(
            reverse(zaakinformatieobjecttype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because no changes are made to the zaakinformatieobjecttype, a code 304 should be
        returned
        """
        zaakinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory.create(
            volgnummer=1
        )
        etag = self.client.get(reverse(zaakinformatieobjecttype))["ETag"]

        response = self.client.get(
            reverse(zaakinformatieobjecttype), headers={"if-none-match": etag}
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class ZaakTypeCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaaktype_get_cache_header(self):
        zaaktype = ZaakTypeFactory.create()

        response = self.client.get(reverse(zaaktype))

        self.assertHasETag(response)

    def test_zaaktype_head_cache_header(self):
        zaaktype = ZaakTypeFactory.create()

        self.assertHeadHasETag(reverse(zaaktype))

    def test_head_in_apischema(self):
        spec = get_spec("catalogi")

        endpoint = spec["paths"]["/zaaktypen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaaktype = ZaakTypeFactory.create()
        etag = self.client.get(reverse(zaaktype))["ETag"]
        response = self.client.get(reverse(zaaktype), headers={"if-none-match": etag})

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaaktype = ZaakTypeFactory.create()

        response = self.client.get(
            reverse(zaaktype), headers={"if-none-match": '"not-an-md5"'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakTypeCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
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
        Because changes are made to the zaaktype, a code 200 should be
        returned
        """
        zaaktype = ZaakTypeFactory.create(toelichting="bla")
        etag = self.client.get(reverse(zaaktype))["ETag"]

        zaaktype.toelichting = "same"
        zaaktype.save()

        response = self.client.get(reverse(zaaktype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_changes_gives_304(self):
        """
        Because changes are made to the zaaktype, a code 200 should be
        returned
        """
        zaaktype = ZaakTypeFactory.create(toelichting="bla")
        etag = self.client.get(reverse(zaaktype))["ETag"]

        response = self.client.get(reverse(zaaktype), headers={"if-none-match": etag})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)


class M2MRelationCachingTests(JWTAuthMixin, APITransactionTestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self._create_credentials(
            self.client_id,
            self.secret,
            self.heeft_alle_autorisaties,
            self.max_vertrouwelijkheidaanduiding,
        )

    def test_changing_besluittype_zaaktype_m2m_invalidates_both_etags(self):
        """
        Changing the M2M should modify both resources, resulting in 200 for
        when both resources are retrieved
        """
        besluittype = BesluitTypeFactory.create()
        besluittype_etag = self.client.get(reverse(besluittype))["ETag"]

        zaaktype = ZaakTypeFactory.create()
        zaaktype_etag = self.client.get(reverse(zaaktype))["ETag"]

        besluittype.zaaktypen.set([zaaktype])
        besluittype.save()

        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": besluittype_etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse(zaaktype), headers={"if-none-match": zaaktype_etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_changing_besluittype_informatieobjecttype_m2m_invalidates_both_etags(self):
        """
        Changing the M2M should modify both resources, resulting in 200 for
        when both resources are retrieved
        """
        besluittype = BesluitTypeFactory.create()
        besluittype_etag = self.client.get(reverse(besluittype))["ETag"]

        zaaktype = ZaakTypeFactory.create()
        zaaktype_etag = self.client.get(reverse(zaaktype))["ETag"]

        besluittype.zaaktypen.set([zaaktype])
        besluittype.save()

        response = self.client.get(
            reverse(besluittype), headers={"if-none-match": besluittype_etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse(zaaktype), headers={"if-none-match": zaaktype_etag}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
