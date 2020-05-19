"""
Guarantee that the proper authorization amchinery is in place.
"""
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ..api.scopes import SCOPE_BESLUITEN_AANMAKEN, SCOPE_BESLUITEN_ALLES_LEZEN
from ..models import BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import serialise_eio

BESLUITTYPE_EXTERNAL = (
    "https://externe.catalogus.nl/api/v1/besluiten/b71f72ef-198d-44d8-af64-ae1932df830a"
)


@override_settings(CMIS_ENABLED=True)
class BesluitScopeForbiddenCMISTests(AuthCheckMixin, APICMISTestCase):
    def test_cannot_create_besluit_without_correct_scope(self):
        url = reverse("besluit-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.register_uri("GET", eio_url, json=serialise_eio(eio, eio_url))
        bio = BesluitInformatieObjectFactory.create(
            besluit=besluit, informatieobject=eio_url
        )
        urls = [
            reverse("besluit-list"),
            reverse(besluit),
            reverse("besluitinformatieobject-list"),
            reverse(bio),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


@override_settings(CMIS_ENABLED=True)
class BioReadCMISTests(JWTAuthMixin, APICMISTestCase):

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
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.register_uri("GET", eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit=besluit1, informatieobject=eio1_url
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.register_uri("GET", eio2_url, json=serialise_eio(eio2, eio2_url))
        BesluitInformatieObjectFactory.create(
            besluit=besluit2, informatieobject=eio2_url
        )

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
        self.adapter.register_uri(
            "GET",
            informatieobject_url,
            json=serialise_eio(informatieobject, informatieobject_url),
        )

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
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class InternalBesluittypeScopeTests(JWTAuthMixin, APICMISTestCase):
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
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.register_uri("GET", eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype, informatieobject=eio1_url,
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.register_uri("GET", eio2_url, json=serialise_eio(eio2, eio2_url))
        BesluitInformatieObjectFactory.create(
            besluit__besluittype=BESLUITTYPE_EXTERNAL, informatieobject=eio2_url,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    def test_bio_retrieve(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.register_uri("GET", eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype, informatieobject=eio1_url,
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.register_uri("GET", eio2_url, json=serialise_eio(eio2, eio2_url))
        bio2 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=BESLUITTYPE_EXTERNAL, informatieobject=eio2_url,
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
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalBesluittypeScopeCMISTests(JWTAuthMixin, APICMISTestCase):
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
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.register_uri("GET", eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype, informatieobject=eio1_url
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.register_uri("GET", eio2_url, json=serialise_eio(eio2, eio2_url))
        BesluitInformatieObjectFactory.create(
            besluit__besluittype="https://externe.catalogus.nl/api/v1/besluiten/1",
            informatieobject=eio2_url,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]["besluit"], f"http://testserver{besluit_url}")

    def test_bio_retrieve(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.register_uri("GET", eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit__besluittype=self.besluittype, informatieobject=eio1_url
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.register_uri("GET", eio2_url, json=serialise_eio(eio2, eio2_url))
        bio2 = BesluitInformatieObjectFactory.create(
            besluit__besluittype="https://externe.catalogus.nl/api/v1/besluiten/1",
            informatieobject=eio2_url,
        )

        url1 = reverse(bio1)
        url2 = reverse(bio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )
