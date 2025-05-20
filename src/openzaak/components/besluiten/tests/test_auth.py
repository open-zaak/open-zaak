# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization amchinery is in place.
"""

from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
    SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
    SCOPE_BESLUITEN_BIJWERKEN,
)
from ..models import BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory

BESLUITTYPE_EXTERNAL = (
    "https://externe.catalogus.nl/api/v1/besluiten/b71f72ef-198d-44d8-af64-ae1932df830a"
)
BESLUITTYPE_EXTERNAL2 = (
    "https://externe.catalogus.nl/api/v1/besluiten/77792ada-3a7b-45a4-9239-f2532b61ad35"
)


class BesluitScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_besluit_without_correct_scope(self):
        url = reverse("besluit-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        besluit = BesluitFactory.create()
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        urls = [
            reverse("besluit-list"),
            reverse(besluit),
            reverse("besluitinformatieobject-list"),
            reverse(bio),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


class BesluitReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create()
        super().setUpTestData()

    def test_besluit_list(self):
        """
        Assert you can only list BESLUITen of the besluittypes of your authorization
        """
        BesluitFactory.create(besluittype=self.besluittype)
        BesluitFactory.create()
        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["besluittype"], f"http://testserver{reverse(self.besluittype)}"
        )

    def test_besluit_list_empty_max_vertrouwelijkheidaanduiding(self):
        """
        max_vertrouwelijkheidaanduiding is not used for besluiten
        """
        self.autorisatie.max_vertrouwelijkheidaanduiding = ""
        self.autorisatie.save()

        BesluitFactory.create(besluittype=self.besluittype)
        BesluitFactory.create()
        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["besluittype"], f"http://testserver{reverse(self.besluittype)}"
        )

    def test_besluit_retreive(self):
        """
        Assert you can only read BESLUITen of the besluittypes of your authorization
        """
        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create()
        url1 = reverse(besluit1)
        url2 = reverse(besluit2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        BesluitFactory.create(besluittype=self.besluittype)
        BesluitFactory.create()
        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 2)

    @tag("gh-1661")
    def test_besluit_list_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to see Besluiten in the list view
        that belong to Besluittypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.besluittype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Should be visible
        BesluitFactory.create(besluittype=self.besluittype)

        # Different catalogus, should not be visible
        BesluitFactory.create()

        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["besluittype"], f"http://testserver{reverse(self.besluittype)}"
        )

    @tag("gh-1661")
    def test_besluit_retrieve_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to read Besluiten
        that belong to Besluittypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.besluittype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Different catalogus, should not be visible
        besluit_not_allowed = BesluitFactory.create()

        # Should be visible
        besluit_allowed = BesluitFactory.create(besluittype=self.besluittype)

        response_not_allowed = self.client.get(reverse(besluit_not_allowed))
        response_allowed = self.client.get(reverse(besluit_allowed))

        self.assertEqual(response_not_allowed.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_allowed.status_code, status.HTTP_200_OK)


class BesluitWriteCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [
        SCOPE_BESLUITEN_BIJWERKEN,
        SCOPE_BESLUITEN_AANMAKEN,
        SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
    ]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create(concept=False)
        super().setUpTestData()

        # Different catalogus, should not be allowed
        cls.besluittype_not_allowed = BesluitTypeFactory.create(concept=False)
        cls.applicatie.autorisaties.all().delete()
        CatalogusAutorisatieFactory.create(
            catalogus=cls.besluittype.catalogus,
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )
        cls.besluit_allowed = BesluitFactory.create(besluittype=cls.besluittype)
        cls.besluit_incorrect_catalogus = BesluitFactory.create()

    @tag("gh-1661")
    def test_besluit_create_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to create Besluiten
        that belong to Besluittypen in the Catalogus
        """
        url = reverse("besluit-list")

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.post(
                url,
                {
                    "besluittype": f"http://testserver{reverse(self.besluittype_not_allowed)}",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "ingangsdatum": "2018-12-24",
                    "datum": "2018-12-24",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.post(
                url,
                {
                    "besluittype": f"http://testserver{reverse(self.besluittype)}",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "ingangsdatum": "2018-12-24",
                    "datum": "2018-12-24",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

    @tag("gh-1661")
    def test_besluit_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to update Besluiten
        that belong to Besluittypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.put(
                reverse(self.besluit_incorrect_catalogus),
                {
                    "besluittype": f"http://testserver{reverse(self.besluit_incorrect_catalogus.besluittype)}",
                    "verantwoordelijkeOrganisatie": self.besluit_incorrect_catalogus.verantwoordelijke_organisatie,
                    "ingangsdatum": self.besluit_incorrect_catalogus.ingangsdatum,
                    "datum": self.besluit_incorrect_catalogus.datum,
                    "toelichting": "aangepast",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.put(
                reverse(self.besluit_allowed),
                {
                    "besluittype": f"http://testserver{reverse(self.besluittype)}",
                    "verantwoordelijkeOrganisatie": self.besluit_allowed.verantwoordelijke_organisatie,
                    "ingangsdatum": self.besluit_allowed.ingangsdatum,
                    "datum": self.besluit_allowed.datum,
                    "toelichting": "aangepast",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_besluit_partial_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to partially update Besluiten
        that belong to Besluittypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.patch(
                reverse(self.besluit_incorrect_catalogus), {"toelichting": "aangepast"}
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.patch(
                reverse(self.besluit_allowed), {"toelichting": "aangepast"}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_besluit_delete_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to delete Besluiten
        that belong to Besluittypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.delete(reverse(self.besluit_incorrect_catalogus))

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.delete(reverse(self.besluit_allowed))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )


class BioReadTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN, SCOPE_BESLUITEN_AANMAKEN]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create()
        super().setUpTestData()

    def test_list_bio_limited_to_authorized_zaken(self):
        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create()

        url = reverse(BesluitInformatieObject)

        # must show up
        bio1 = BesluitInformatieObjectFactory.create(besluit=besluit1)
        # must not show up
        BesluitInformatieObjectFactory.create(besluit=besluit2)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    @tag("gh-1661")
    def test_list_bio_limited_to_authorized_zaken_with_catalogus_autorisatie(self):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.besluittype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create()

        url = reverse(BesluitInformatieObject)

        # must show up
        bio1 = BesluitInformatieObjectFactory.create(besluit=besluit1)
        # must not show up
        BesluitInformatieObjectFactory.create(besluit=besluit2)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    def test_create_bio_limited_to_authorized_besluiten(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        informatieobject_url = f"http://testserver{reverse(informatieobject)}"

        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create()

        self.besluittype.informatieobjecttypen.add(
            informatieobject.informatieobjecttype
        )
        besluit2.besluittype.informatieobjecttypen.add(
            informatieobject.informatieobjecttype
        )

        besluit_uri1 = reverse(besluit1)
        besluit_url1 = f"http://testserver{besluit_uri1}"

        besluit_uri2 = reverse(besluit2)
        besluit_url2 = f"http://testserver{besluit_uri2}"

        url1 = reverse("besluitinformatieobject-list")
        url2 = reverse("besluitinformatieobject-list")

        data1 = {"informatieobject": informatieobject_url, "besluit": besluit_url1}
        data2 = {"informatieobject": informatieobject_url, "besluit": besluit_url2}

        response1 = self.client.post(url1, data1)
        response2 = self.client.post(url2, data2)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class InternalBesluittypeScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create()

        super().setUpTestData()

    def test_besluit_list(self):
        BesluitFactory.create(besluittype=self.besluittype)
        BesluitFactory.create(besluittype=BESLUITTYPE_EXTERNAL)
        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["besluittype"], f"http://testserver{reverse(self.besluittype)}"
        )

    def test_besluit_list_internal_and_external_with_filtering(self):
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes or [],
            zaaktype="",
            informatieobjecttype="",
            besluittype=BESLUITTYPE_EXTERNAL,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        # Should show up
        BesluitFactory.create(
            besluittype=self.besluittype, verantwoordelijke_organisatie="000000000"
        )
        BesluitFactory.create(
            besluittype=BESLUITTYPE_EXTERNAL, verantwoordelijke_organisatie="000000000"
        )

        # Should not show up due to filtering
        BesluitFactory.create(
            besluittype=self.besluittype, verantwoordelijke_organisatie="123456789"
        )
        # Should not show up due to lacking permissions
        BesluitFactory.create(
            besluittype=BESLUITTYPE_EXTERNAL2, verantwoordelijke_organisatie="000000000"
        )
        url = reverse("besluit-list")

        response = self.client.get(url, {"verantwoordelijkeOrganisatie": "000000000"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["besluittype"], BESLUITTYPE_EXTERNAL)
        self.assertEqual(
            results[1]["besluittype"], f"http://testserver{reverse(self.besluittype)}"
        )

    def test_besluit_retrieve(self):
        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create(besluittype=BESLUITTYPE_EXTERNAL)
        url1 = reverse(besluit1)
        url2 = reverse(besluit2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_bio_list(self):
        url = reverse(BesluitInformatieObject)
        # must show up
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype,
        )
        # must not show up
        BesluitInformatieObjectFactory.create(besluit__besluittype=BESLUITTYPE_EXTERNAL)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    def test_bio_retrieve(self):
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype
        )
        bio2 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=BESLUITTYPE_EXTERNAL
        )

        url1 = reverse(bio1)
        url2 = reverse(bio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalBesluittypeScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    besluittype = BESLUITTYPE_EXTERNAL
    component = ComponentTypes.brc

    def test_besluit_list(self):
        BesluitFactory.create(besluittype=self.besluittype)
        BesluitFactory.create(
            besluittype="https://externe.catalogus.nl/api/v1/besluiten/1"
        )
        url = reverse("besluit-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["besluittype"], self.besluittype)

    def test_besluit_retrieve(self):
        besluit1 = BesluitFactory.create(besluittype=self.besluittype)
        besluit2 = BesluitFactory.create(
            besluittype="https://externe.catalogus.nl/api/v1/besluiten/1"
        )
        url1 = reverse(besluit1)
        url2 = reverse(besluit2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_bio_list(self):
        url = reverse(BesluitInformatieObject)
        # must show up
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype
        )
        # must not show up
        BesluitInformatieObjectFactory.create(
            besluit__besluittype="https://externe.catalogus.nl/api/v1/besluiten/1"
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    def test_bio_retrieve(self):
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype
        )
        bio2 = BesluitInformatieObjectFactory.create(
            besluit__besluittype="https://externe.catalogus.nl/api/v1/besluiten/1",
        )

        url1 = reverse(bio1)
        url2 = reverse(bio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )
