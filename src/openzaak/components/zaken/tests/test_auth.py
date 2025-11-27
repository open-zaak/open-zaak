# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""

from django.test import override_settings, tag
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, reverse
from vng_api_common.tests.schema import get_validation_errors

from openzaak.components.autorisaties.tests.factories import (
    AutorisatieFactory,
    CatalogusAutorisatieFactory,
)
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    EigenschapFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from ..models import Zaak, ZaakBesluit, ZaakInformatieObject
from .factories import (
    KlantContactFactory,
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    SubStatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakNotitieFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_READ_KWARGS, ZAAK_WRITE_KWARGS, get_operation_url


class ZakenScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_zaak_without_correct_scope(self):
        url = reverse("zaak-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        zaak = ZaakFactory.create()
        status = StatusFactory.create()
        zaak_object = ZaakObjectFactory.create()
        resultaat = ResultaatFactory.create()
        urls = [
            reverse("zaak-list"),
            reverse(zaak),
            reverse("status-list"),
            reverse(status),
            reverse("resultaat-list"),
            reverse(resultaat),
            reverse("zaakobject-list"),
            reverse(zaak_object),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get", request_kwargs=ZAAK_READ_KWARGS)


class ZaakReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_zaak_list(self):
        """
        Assert you can only list ZAAKen of the zaaktypes and vertrouwelijkheidaanduiding
        of your authorization
        """
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_zaak_list_multiple_confidentialities(self):
        """
        Assert you can be authorized for multiple zaaktypen
        """
        zaaktype2 = ZaakTypeFactory.create()
        AutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
            zaaktype=f"http://testserver{reverse(zaaktype2)}",
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
        )
        # should show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        # should not show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0]["zaaktype"], f"http://testserver{reverse(zaaktype2)}"
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.geheim,
        )
        self.assertEqual(
            results[1]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )
        self.assertEqual(
            results[1]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_zaak_retreive(self):
        """
        Assert you can only read ZAAKen of the zaaktypes and vertrouwelijkheidaanduiding
        of your authorization
        """
        zaak1 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    @tag("gh-1661")
    def test_zaak_list_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to see Zaken in the list view
        that belong to Zaaktypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Should be visible
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # Different catalogus, should not be visible
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # Correct catalogus, but VA is too high, should not be visible
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        # Different catalogus, should not be visible
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    @tag("gh-1661")
    def test_zaak_list_with_catalogus_autorisatie_and_regular_autorisaties(self):
        """
        Assert that CatalogusAutorisatie and regular Autorisaties can be used together
        """
        zaaktype2 = ZaakTypeFactory.create()
        zaaktype3 = ZaakTypeFactory.create()
        CatalogusAutorisatieFactory.create(
            catalogus=zaaktype2.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        CatalogusAutorisatieFactory.create(
            catalogus=zaaktype3.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        # Should be visible because of regular Autorisatie
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # Should be visible because of first CatalogusAutorisatie
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )
        # Should be visible because of second first CatalogusAutorisatie
        ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        # Different catalogus, should not be visible
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # Correct zaaktype, but VA is too high, should not be visible
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        # Correct catalogus, but VA is too high, should not be visible
        ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 3)
        self.assertEqual(
            results[0]["zaaktype"], f"http://testserver{reverse(zaaktype3)}"
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(
            results[1]["zaaktype"], f"http://testserver{reverse(zaaktype2)}"
        )
        self.assertEqual(
            results[1]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )
        self.assertEqual(
            results[2]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )
        self.assertEqual(
            results[2]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    @tag("gh-1661")
    def test_zaak_retrieve_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to read Zaken
        that belong to Zaaktypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Not part of catalogus
        zaak1 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # vertrouwelijkheidaanduiding too high
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        # allowed to access!
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)
        response3 = self.client.get(url3, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 4)


class ZaakWriteCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_ALLES_VERWIJDEREN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        # Different catalogus, should not be allowed
        cls.zaaktype_not_allowed = ZaakTypeFactory.create(concept=False)
        cls.applicatie.autorisaties.all().delete()
        CatalogusAutorisatieFactory.create(
            catalogus=cls.zaaktype.catalogus,
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

        cls.zaak_allowed = ZaakFactory.create(
            zaaktype=cls.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        cls.zaak_incorrect_catalogus = ZaakFactory.create()
        cls.zaak_incorrect_va = ZaakFactory.create(
            zaaktype=cls.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

    @tag("gh-1661")
    def test_zaak_create_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to create Zaken
        that belong to Zaaktypen in the Catalogus
        """
        url = reverse("zaak-list")

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.post(
                url,
                {
                    "zaaktype": f"http://testserver{reverse(self.zaaktype_not_allowed)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.post(
                url,
                {
                    "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.post(
                url,
                {
                    "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

    @tag("gh-1661")
    def test_zaak_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to update Zaken
        that belong to Zaaktypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.put(
                reverse(self.zaak_incorrect_catalogus),
                {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.put(
                reverse(self.zaak_incorrect_va),
                {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.put(
                reverse(self.zaak_allowed),
                {
                    "title": "foo",
                    "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_zaak_partial_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to partially Zaken
        that belong to Zaaktypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.patch(
                reverse(self.zaak_incorrect_catalogus),
                {"title": "foo"},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.patch(
                reverse(self.zaak_incorrect_va), {"title": "foo"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.patch(
                reverse(self.zaak_allowed), {"title": "foo"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_zaak_delete_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to delete Zaken
        that belong to Zaaktypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.delete(
                reverse(self.zaak_incorrect_catalogus), **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.delete(
                reverse(self.zaak_incorrect_va), **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.delete(
                reverse(self.zaak_allowed), **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )


class ZaakListPerformanceTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim
    component = ComponentTypes.zrc
    heeft_alle_autorisaties = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # we're managing those directly in the test itself
        cls.autorisatie.delete()

    @override_settings(ALLOWED_HOSTS=["example.com", "testserver"])
    def test_zaak_list_performance(self):
        """
        Test the performance of zaak-list when authorizations are checked.

        This is a regression test for #1057 where the number of queries scaled with
        the amount of zaaktypen involved in the permissions.
        """
        # queries not directly involved with this endpoint in particular
        BASE_NUM_QUERIES = 4
        # queries because of the permission checks
        PERMISSION_CHECK_NUM_QUERIES = 6
        # queries because of the list endpoint itself
        ENDPOINT_NUM_QUERIES = 12
        TOTAL_EXPECTED_QUERIES = (
            BASE_NUM_QUERIES + PERMISSION_CHECK_NUM_QUERIES + ENDPOINT_NUM_QUERIES
        )

        # check with different orders of magnitude for the number of zaaktypen the client
        # is authorized for
        num_zaaktypen_cases = (1, 10, 100)

        for num_zaaktypen in num_zaaktypen_cases:
            # reset state
            Zaak.objects.all().delete()
            ZaakType.objects.all().delete()
            self.applicatie.save()
            catalogus = CatalogusFactory.create()

            CatalogusAutorisatieFactory.create(
                applicatie=self.applicatie,
                component=self.component,
                scopes=self.scopes,
                max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
                catalogus=catalogus,
            )
            # Create unrelated CatalogusAutorisatie
            CatalogusAutorisatieFactory.create(
                applicatie=self.applicatie,
                component=self.component,
                scopes=self.scopes,
                max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
                catalogus=CatalogusFactory.create(),
            )

            with self.subTest(num_zaaktypen=num_zaaktypen):
                ZaakTypeFactory.create_batch(
                    num_zaaktypen, concept=False, catalogus=catalogus
                )
                # create a zaak for response data
                zaaktype = ZaakType.objects.last()
                ZaakFactory.create(zaaktype=zaaktype)

                with self.assertNumQueries(TOTAL_EXPECTED_QUERIES):
                    response = self.client.get(reverse("zaak-list"), **ZAAK_READ_KWARGS)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["count"], 1)


class StatusTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_statussen_limited_to_authorized_zaken(self):
        url = reverse("status-list")
        # must show up
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        StatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(status1)}"
        )

    @tag("gh-1661")
    def test_list_statussen_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("status-list")
        # must show up
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        StatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(status1)}"
        )

    def test_create_status_limited_to_authorized_zaken(self):
        url = reverse("status-list")

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        rol = RolFactory.create(zaak=zaak, roltype__zaaktype=zaak.zaaktype)
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "statustype": f"http://testserver{reverse(statustype)}",
            "datumStatusGezet": "2023-01-01T00:00:00",
            "gezetdoor": f"http://testserver{reverse(rol)}",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaak1 = ZaakFactory.create()
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        for zaak in [zaak1, zaak2]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                statustype = StatusTypeFactory.create(zaaktype=zaak1.zaaktype)
                rol = RolFactory.create(zaak=zaak, roltype__zaaktype=zaak.zaaktype)
                data = {
                    "zaak": f"http://testserver{reverse(zaak)}",
                    "statustype": f"http://testserver{reverse(statustype)}",
                    "datumStatusGezet": "2023-01-01T00:00:00",
                    "gezetdoor": f"http://testserver{reverse(rol)}",
                }
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_operations_validate_main_object(self):
        url = reverse("status-list")

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        rol = RolFactory.create(zaak=zaak, roltype__zaaktype=zaak.zaaktype)

        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                url,
                {
                    "zaak": "http://example.com",
                    "statustype": f"http://testserver{reverse(statustype)}",
                    "datumStatusGezet": "2023-01-01T00:00:00",
                    "gezetdoor": f"http://testserver{reverse(rol)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                url,
                {
                    "zaak": f"http://testserver{reverse(old_zaak)}",
                    "statustype": f"http://testserver{reverse(statustype)}",
                    "datumStatusGezet": "2023-01-01T00:00:00",
                    "gezetdoor": f"http://testserver{reverse(rol)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                url,
                {
                    "zaak": f"http://testserver{reverse(self.zaaktype)}",
                    "statustype": f"http://testserver{reverse(statustype)}",
                    "datumStatusGezet": "2023-01-01T00:00:00",
                    "gezetdoor": f"http://testserver{reverse(rol)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class ZaakNotitieTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc
    url = reverse("zaaknotitie-list")

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaaknotitie_limited_to_authorized_zaken(self):
        # must show up
        notitie = ZaakNotitieFactory.create(
            gerelateerd_aan__zaaktype=self.zaaktype,
            gerelateerd_aan__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakNotitieFactory.create(
            gerelateerd_aan__zaaktype=self.zaaktype,
            gerelateerd_aan__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        ZaakNotitieFactory.create(
            gerelateerd_aan__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(notitie)}"
        )

    def test_create_zaaknotitie_limited_to_authorized_zaken(self):
        zaak1 = ZaakFactory.create()
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        for zaak in [zaak1, zaak2]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                response = self.client.post(self.url, {"gerelateerdAan": reverse(zaak)})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            "onderwerp": "Test onderwerp",
            "tekst": "Test tekst",
            "aangemaaktDoor": "Test",
            "gerelateerdAan": reverse(zaak3),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_write_operations_forbidden(self):
        # scope not provided for writes, so this should 403 (not 404!)
        notitie = ZaakNotitieFactory.create(
            gerelateerd_aan__zaaktype=self.zaaktype,
            gerelateerd_aan__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(notitie)

        for method in ["put", "patch", "delete"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_operations_validate_main_object(self):
        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                reverse("zaaknotitie-list"),
                {
                    "onderwerp": "Test onderwerp",
                    "tekst": "Test tekst",
                    "aangemaaktDoor": "Test",
                    "gerelateerdAan": "http://example.com",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "gerelateerdAan")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                reverse("zaaknotitie-list"),
                {
                    "onderwerp": "Test onderwerp",
                    "tekst": "Test tekst",
                    "aangemaaktDoor": "Test",
                    "gerelateerdAan": f"http://testserver{reverse(old_zaak)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "gerelateerdAan")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                reverse("zaaknotitie-list"),
                {
                    "onderwerp": "Test onderwerp",
                    "tekst": "Test tekst",
                    "aangemaaktDoor": "Test",
                    "gerelateerdAan": f"http://testserver{reverse(self.zaaktype)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "gerelateerdAan")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class ResultaatTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_resultaat_limited_to_authorized_zaken(self):
        url = reverse("resultaat-list")
        # must show up
        resultaat = ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        ResultaatFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(resultaat)}"
        )

    @tag("gh-1661")
    def test_list_resultaat_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("resultaat-list")
        # must show up
        resultaat = ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        ResultaatFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(resultaat)}"
        )

    def test_write_operations_forbidden(self):
        # scope not provided for writes, so this should 403 (not 404!)
        resultaat = ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(resultaat)

        for method in ["put", "patch", "delete"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_resultaat_limited_to_authorized_zaken(self):
        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        resultaattype = ResultaatTypeFactory.create(zaaktype=self.zaaktype)

        with self.subTest(
            zaaktype=zaak1.zaaktype,
            vertrouwelijkheidaanduiding=zaak1.vertrouwelijkheidaanduiding,
        ):
            response = self.client.post(
                reverse("resultaat-list"),
                {
                    "zaak": f"http://testserver{reverse(zaak1)}",
                    "resultaattype": f"http://testserver{reverse(resultaattype)}",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

        for zaak in (zaak2, zaak3):
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                response = self.client.post(
                    reverse("resultaat-list"),
                    {
                        "zaak": f"http://testserver{reverse(zaak)}",
                        "resultaattype": f"http://testserver{reverse(resultaattype)}",
                    },
                )

                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN, response.data
                )

    def test_write_operations_validate_main_object(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype=self.zaaktype)

        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                reverse("resultaat-list"),
                {
                    "zaak": "http://example.com",
                    "resultaattype": f"http://testserver{reverse(resultaattype)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                reverse("resultaat-list"),
                {
                    "zaak": f"http://testserver{reverse(old_zaak)}",
                    "resultaattype": f"http://testserver{reverse(resultaattype)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                reverse("resultaat-list"),
                {
                    "zaak": f"http://testserver{reverse(self.zaaktype)}",
                    "resultaattype": f"http://testserver{reverse(resultaattype)}",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class ZaakObjectTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakobject_limited_to_authorized_zaken(self):
        url = reverse("zaakobject-list")
        # must show up
        zaakobject = ZaakObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(zaakobject)}"
        )

    @tag("gh-1661")
    def test_list_zaakobject_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("zaakobject-list")
        # must show up
        zaakobject = ZaakObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(zaakobject)}"
        )

    def test_create_zaakobject_limited_to_authorized_zaken(self):
        url = reverse("zaakobject-list")
        zaak1 = ZaakFactory.create()
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        for zaak in [zaak1, zaak2]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                response = self.client.post(url, {"zaak": reverse(zaak)})

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_operations_validate_main_object(self):
        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                reverse("zaakobject-list"),
                {"zaak": "http://example.com"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                reverse("zaakobject-list"),
                {"zaak": f"http://testserver{reverse(old_zaak)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                reverse("zaakobject-list"),
                {"zaak": f"http://testserver{reverse(self.zaaktype)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class ZaakInformatieObjectTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakinformatieobject_limited_to_authorized_zaken(self):
        # must show up
        zio1 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")

    @tag("gh-1661")
    def test_list_zaakinformatieobject_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # must show up
        zio1 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")

    def test_create_zaakinformatieobject_without_zaak(self):
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        enkelvoudiginformatieobject = EnkelvoudigInformatieObjectFactory.create()
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype,
            informatieobjecttype=enkelvoudiginformatieobject.informatieobjecttype,
        )
        _status = StatusFactory.create(zaak=zaak)

        zaakinformatieobject = {
            "titel": "string",
            "informatieobject": f"http://testserver{reverse(enkelvoudiginformatieobject)}",
            "beschrijving": "string",
            "vernietigingsdatum": "2019-08-24T14:15:22Z",
            "status": f"http://testserver{reverse(_status)}",
        }

        url = reverse("zaakinformatieobject-list")

        response = self.client.post(url, zaakinformatieobject)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "required")

    def test_write_operations_validate_main_object(self):
        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                reverse("zaakinformatieobject-list"),
                {"zaak": "http://example.com"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                reverse("zaakinformatieobject-list"),
                {"zaak": f"http://testserver{reverse(old_zaak)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                reverse("zaakinformatieobject-list"),
                {"zaak": f"http://testserver{reverse(self.zaaktype)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class ZaakEigenschapTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakeigenschap_limited_to_authorized_zaken(self):
        # must show up
        eigenschap1 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        eigenschap2 = ZaakEigenschapFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap3 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        with self.subTest(
            zaaktype=eigenschap1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=eigenschap1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(
                "zaakeigenschap-list", kwargs={"zaak_uuid": eigenschap1.zaak.uuid}
            )
            eigenschap1_url = reverse(
                eigenschap1, kwargs={"zaak_uuid": eigenschap1.zaak.uuid}
            )

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]["url"], f"http://testserver{eigenschap1_url}"
            )

        # not allowed to see these
        for eigenschap in (eigenschap2, eigenschap3):
            with self.subTest(
                zaaktype=eigenschap.zaak.zaaktype,
                vertrouwelijkheidaanduiding=eigenschap.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(
                    "zaakeigenschap-list", kwargs={"zaak_uuid": eigenschap.zaak.uuid}
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @tag("gh-1661")
    def test_list_zaakeigenschap_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # must show up
        eigenschap1 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        eigenschap2 = ZaakEigenschapFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap3 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        with self.subTest(
            zaaktype=eigenschap1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=eigenschap1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(
                "zaakeigenschap-list", kwargs={"zaak_uuid": eigenschap1.zaak.uuid}
            )
            eigenschap1_url = reverse(
                eigenschap1, kwargs={"zaak_uuid": eigenschap1.zaak.uuid}
            )

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]["url"], f"http://testserver{eigenschap1_url}"
            )

        # not allowed to see these
        for eigenschap in (eigenschap2, eigenschap3):
            with self.subTest(
                zaaktype=eigenschap.zaak.zaaktype,
                vertrouwelijkheidaanduiding=eigenschap.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(
                    "zaakeigenschap-list", kwargs={"zaak_uuid": eigenschap.zaak.uuid}
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_zaakeigenschap_limited_to_authorized_zaken(self):
        # must show up
        eigenschap1 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        eigenschap2 = ZaakEigenschapFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap3 = ZaakEigenschapFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        with self.subTest(
            zaaktype=eigenschap1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=eigenschap1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(eigenschap1, kwargs={"zaak_uuid": eigenschap1.zaak.uuid})

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for eigenschap in (eigenschap2, eigenschap3):
            with self.subTest(
                zaaktype=eigenschap.zaak.zaaktype,
                vertrouwelijkheidaanduiding=eigenschap.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(eigenschap, kwargs={"zaak_uuid": eigenschap.zaak.uuid})

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_zaakeigenschap_limited_to_authorized_zaken(self):
        eigenschap = EigenschapFactory.create(zaaktype=self.zaaktype)
        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        with self.subTest(
            zaaktype=zaak1.zaaktype,
            vertrouwelijkheidaanduiding=zaak1.vertrouwelijkheidaanduiding,
        ):
            url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak1.uuid)

            response = self.client.post(
                url,
                {
                    "zaak": reverse(zaak1),
                    "eigenschap": f"http://testserver{reverse(eigenschap)}",
                    "waarde": "test",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

        for zaak in (zaak2, zaak3):
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

                response = self.client.post(
                    url,
                    {
                        "zaak": reverse(zaak),
                        "eigenschap": reverse(eigenschap),
                        "waarde": "test",
                    },
                )

                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN, response.data
                )


class SubStatusTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_STATUSSEN_TOEVOEGEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_substatus_limited_to_authorized_zaken(self):
        # must show up
        substatus1 = SubStatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        SubStatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        SubStatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        with self.subTest(
            zaaktype=substatus1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=substatus1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse("substatus-list")
            substatus1_url = reverse(substatus1)

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(response_data["count"], 1)
            self.assertEqual(
                response_data["results"][0]["url"], f"http://testserver{substatus1_url}"
            )

    def test_detail_substatus_limited_to_authorized_zaken(self):
        # must show up
        substatus1 = SubStatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        substatus2 = SubStatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        substatus3 = SubStatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        with self.subTest(
            zaaktype=substatus1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=substatus1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(substatus1)

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for substatus in (substatus2, substatus3):
            with self.subTest(
                zaaktype=substatus.zaak.zaaktype,
                vertrouwelijkheidaanduiding=substatus.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(substatus)

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_substatus_limited_to_authorized_zaken(self):
        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        status1 = StatusFactory.create(zaak=zaak1)
        status2 = StatusFactory.create(zaak=zaak2)
        status3 = StatusFactory.create(zaak=zaak3)

        with self.subTest(
            zaaktype=zaak1.zaaktype,
            vertrouwelijkheidaanduiding=zaak1.vertrouwelijkheidaanduiding,
        ):
            url = reverse("substatus-list")

            response = self.client.post(
                url,
                {
                    "zaak": reverse(zaak1),
                    "status": reverse(status1),
                    "omschrijving": "test",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

        for zaak, stat in [(zaak2, status2), (zaak3, status3)]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse("substatus-list")

                response = self.client.post(
                    url,
                    {
                        "zaak": reverse(zaak),
                        "status": reverse(stat),
                        "omschrijving": "test",
                    },
                )

                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN, response.data
                )

    def test_write_operations_validate_main_object(self):
        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                reverse("substatus-list"),
                {"zaak": "http://example.com"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                reverse("substatus-list"),
                {"zaak": f"http://testserver{reverse(old_zaak)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                reverse("substatus-list"),
                {"zaak": f"http://testserver{reverse(self.zaaktype)}"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )


class RolReadTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_rol_limited_to_authorized_zaken(self):
        url = reverse("rol-list")
        # must show up
        rol = RolFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        RolFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        RolFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(rol)}")

    @tag("gh-1661")
    def test_list_rol_limited_to_authorized_zaken_with_catalogus_autorisatie(self):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("rol-list")
        # must show up
        rol = RolFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        RolFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        RolFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(rol)}")


class ZaakBesluitTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakbesluit_limited_to_authorized_zaken(self):
        # must show up
        besluit1 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit1 = ZaakBesluit.objects.get(besluit=besluit1, zaak=besluit1.zaak)
        # must not show up
        besluit2 = BesluitFactory.create(
            for_zaak=True,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit2 = ZaakBesluit.objects.get(besluit=besluit2, zaak=besluit2.zaak)
        # must not show up
        besluit3 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        zaakbesluit3 = ZaakBesluit.objects.get(besluit=besluit3, zaak=besluit3.zaak)

        with self.subTest(
            zaaktype=zaakbesluit1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaakbesluit1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(
                "zaakbesluit-list", kwargs={"zaak_uuid": zaakbesluit1.zaak.uuid}
            )
            zaakbesluit1_url = get_operation_url(
                "zaakbesluit_read",
                zaak_uuid=zaakbesluit1.zaak.uuid,
                uuid=zaakbesluit1.uuid,
            )

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]["url"], f"http://testserver{zaakbesluit1_url}"
            )

        # not allowed to see these
        for zaakbesluit in (zaakbesluit2, zaakbesluit3):
            with self.subTest(
                zaaktype=zaakbesluit.zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaakbesluit.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(
                    "zaakbesluit-list", kwargs={"zaak_uuid": zaakbesluit.zaak.uuid}
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @tag("gh-1661")
    def test_list_zaakbesluit_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.zaaktype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # must show up
        besluit1 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit1 = ZaakBesluit.objects.get(besluit=besluit1, zaak=besluit1.zaak)
        # must not show up
        besluit2 = BesluitFactory.create(
            for_zaak=True,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit2 = ZaakBesluit.objects.get(besluit=besluit2, zaak=besluit2.zaak)
        # must not show up
        besluit3 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        zaakbesluit3 = ZaakBesluit.objects.get(besluit=besluit3, zaak=besluit3.zaak)

        with self.subTest(
            zaaktype=zaakbesluit1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaakbesluit1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = reverse(
                "zaakbesluit-list", kwargs={"zaak_uuid": zaakbesluit1.zaak.uuid}
            )
            zaakbesluit1_url = get_operation_url(
                "zaakbesluit_read",
                zaak_uuid=zaakbesluit1.zaak.uuid,
                uuid=zaakbesluit1.uuid,
            )

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]["url"], f"http://testserver{zaakbesluit1_url}"
            )

        # not allowed to see these
        for zaakbesluit in (zaakbesluit2, zaakbesluit3):
            with self.subTest(
                zaaktype=zaakbesluit.zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaakbesluit.zaak.vertrouwelijkheidaanduiding,
            ):
                url = reverse(
                    "zaakbesluit-list", kwargs={"zaak_uuid": zaakbesluit.zaak.uuid}
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_zaakbesluit_limited_to_authorized_zaken(self):
        # must show up
        besluit1 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit1 = ZaakBesluit.objects.get(besluit=besluit1, zaak=besluit1.zaak)
        # must not show up
        besluit2 = BesluitFactory.create(
            for_zaak=True,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakbesluit2 = ZaakBesluit.objects.get(besluit=besluit2, zaak=besluit2.zaak)
        # must not show up
        besluit3 = BesluitFactory.create(
            for_zaak=True,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        zaakbesluit3 = ZaakBesluit.objects.get(besluit=besluit3, zaak=besluit3.zaak)

        with self.subTest(
            zaaktype=zaakbesluit1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaakbesluit1.zaak.vertrouwelijkheidaanduiding,
        ):
            url = get_operation_url(
                "zaakbesluit_read",
                zaak_uuid=zaakbesluit1.zaak.uuid,
                uuid=zaakbesluit1.uuid,
            )

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for zaakbesluit in (zaakbesluit2, zaakbesluit3):
            with self.subTest(
                zaaktype=zaakbesluit.zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaakbesluit.zaak.vertrouwelijkheidaanduiding,
            ):
                url = get_operation_url(
                    "zaakbesluit_read",
                    zaak_uuid=zaakbesluit.zaak.uuid,
                    uuid=zaakbesluit.uuid,
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class InternalZaaktypeScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()

        super().setUpTestData()

    def test_zaak_list_internal_and_external(self):
        external_zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        external_zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/d530aa07-3e4e-42ff-9be8-3247b3a6e7e3"

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes or [],
            zaaktype=external_zaaktype1,
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        # Should show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakFactory.create(
            zaaktype=external_zaaktype1,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        # Should not show up, because there should be no overlap between the local and
        # external filters
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        ZaakFactory.create(
            zaaktype=external_zaaktype1,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            zaaktype=external_zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["zaaktype"], external_zaaktype1)
        self.assertEqual(
            results[1]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )

    def test_zaak_list_with_filtering(self):
        """
        Assert that filtering still works when a non superuser application is used
        """
        external_zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        external_zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/d530aa07-3e4e-42ff-9be8-3247b3a6e7e3"

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes or [],
            zaaktype=external_zaaktype1,
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        # Should show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            bronorganisatie="000000000",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        # Should not show up due to filtering
        ZaakFactory.create(
            zaaktype=external_zaaktype1,
            bronorganisatie="736160221",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        # Should not show up due to lacking permissions
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        ZaakFactory.create(
            zaaktype=external_zaaktype1,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            zaaktype=external_zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse("zaak-list")

        response = self.client.get(
            url, {"bronorganisatie": "000000000"}, **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["zaaktype"], f"http://testserver{reverse(self.zaaktype)}"
        )

    def test_zaak_retrieve(self):
        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_statussen_list(self):
        url = reverse("status-list")
        # must show up
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        StatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a",
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(status1)}"
        )

    def test_statussen_retrieve(self):
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        status2 = StatusFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a",
        )
        url1 = reverse(status1)
        url2 = reverse(status2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalZaaktypeScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    component = ComponentTypes.zrc

    def test_zaak_list_external_zaaktype(self):
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakFactory.create(
            zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 1)

    def test_zaak_retrieve(self):
        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_statussen_list(self):
        url = reverse("status-list")
        # must show up
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        StatusFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(status1)}"
        )

    def test_statussen_retrieve(self):
        status1 = StatusFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        status2 = StatusFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(status1)
        url2 = reverse(status2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_resultaten_list(self):
        url = reverse("resultaat-list")
        # must show up
        resultaat = ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            resultaattype="https://externe.catalogus.nl/api/v1/resultaattypen/1",
        )
        # must not show up
        ResultaatFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            resultaattype="https://externe.catalogus.nl/api/v1/resultaattypen/2",
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(resultaat)}"
        )

    def test_resultaten_retrieve(self):
        resultaat1 = ResultaatFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            resultaattype="https://externe.catalogus.nl/api/v1/resultaattypen/1",
        )
        resultaat2 = ResultaatFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            resultaattype="https://externe.catalogus.nl/api/v1/resultaattypen/2",
        )
        url1 = reverse(resultaat1)
        url2 = reverse(resultaat2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaakinformatieobject_list(self):
        # must show up
        zio1 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")

    def test_zaakinformatieobject_retrieve(self):
        zio1 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zio2 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zio1)
        url2 = reverse(zio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@tag("gh-1836")
class ReserveerZaaknummerTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    def test_cannot_reserveer_zaaknummer_without_correct_scope(self):
        url = reverse("zaakidentificatie-list")

        response = self.client.post(url, {"bronorganisatie": "000000000"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class KlantContactTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc
    url = reverse("klantcontact-list")

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_klantcontact_limited_to_authorized_zaken(self):
        # must show up
        klantcontact = KlantContactFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        KlantContactFactory.create(
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        KlantContactFactory.create(
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(klantcontact)}"
        )

    def test_create_klantcontact_limited_to_authorized_zaken(self):
        zaak1 = ZaakFactory.create()
        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        for zaak in [zaak1, zaak2]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            ):
                response = self.client.post(self.url, {"zaak": reverse(zaak)})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            "zaak": reverse(zaak3),
            "datumtijd": "2019-07-22T12:00:00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_write_operations_validate_main_object(self):
        with self.subTest("POST invalid main object url"):
            response = self.client.post(
                self.url,
                {
                    "zaak": "http://example.com",
                    "datumtijd": "2019-07-22T12:00:00",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object uuid"):
            old_zaak = ZaakFactory.create()
            Zaak.objects.filter(uuid=old_zaak.uuid).delete()
            response = self.client.post(
                self.url,
                {
                    "zaak": f"http://testserver{reverse(old_zaak)}",
                    "datumtijd": "2019-07-22T12:00:00",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "object-does-not-exist")
            self.assertEqual(error["reason"], "Dit object bestaat niet in de database")

        with self.subTest("POST invalid main object resource"):
            response = self.client.post(
                self.url,
                {
                    "zaak": f"http://testserver{reverse(self.zaaktype)}",
                    "datumtijd": "2019-07-22T12:00:00",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "zaak")
            self.assertEqual(error["code"], "incorrect_match")
            self.assertEqual(
                error["reason"],
                _("Incorrect resource. Expected: {expected}").format(expected="Zaak"),
            )
