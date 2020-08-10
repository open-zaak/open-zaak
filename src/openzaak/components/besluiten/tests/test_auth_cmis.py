# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Guarantee that the proper authorization amchinery is in place.
"""
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ..api.scopes import SCOPE_BESLUITEN_AANMAKEN, SCOPE_BESLUITEN_ALLES_LEZEN
from ..models import BesluitInformatieObject
from .factories import BesluitInformatieObjectFactory

BESLUITTYPE_EXTERNAL = (
    "https://externe.catalogus.nl/api/v1/besluiten/b71f72ef-198d-44d8-af64-ae1932df830a"
)


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class BesluitScopeForbiddenCMISTests(AuthCheckMixin, APICMISTestCase, OioMixin):
    def test_cannot_read_without_correct_scope(self):
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        bio = BesluitInformatieObjectFactory.create(
            besluit=besluit, informatieobject=eio_url
        )
        urls = [
            reverse("besluitinformatieobject-list"),
            reverse(bio),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class BioReadCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):

    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN, SCOPE_BESLUITEN_AANMAKEN]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create()
        super().setUpTestData()

    def test_list_bio_limited_to_authorized_zaken(self):
        self.create_zaak_besluit_services()
        besluit1 = self.create_besluit(**{"besluittype": self.besluittype})
        besluit2 = self.create_besluit()

        url = reverse(BesluitInformatieObject)

        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        bio1 = BesluitInformatieObjectFactory.create(
            besluit=besluit1, informatieobject=eio1_url
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
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
        self.adapter.get(
            informatieobject_url,
            json=serialise_eio(informatieobject, informatieobject_url),
        )

        self.create_zaak_besluit_services()
        besluit1 = self.create_besluit(**{"besluittype": self.besluittype})
        besluit2 = self.create_besluit()

        self.besluittype.informatieobjecttypen.add(
            informatieobject.informatieobjecttype
        )
        besluit2.besluittype.informatieobjecttypen.add(
            informatieobject.informatieobjecttype
        )

        besluit_url1 = make_absolute_uri(reverse(besluit1))
        besluit_url2 = make_absolute_uri(reverse(besluit2))

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


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class InternalBesluittypeScopeTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    component = ComponentTypes.brc

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create()
        super().setUpTestData()

    def test_bio_list(self):
        url = reverse(BesluitInformatieObject)
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        self.create_zaak_besluit_services()
        bio1 = BesluitInformatieObjectFactory.create(
            informatieobject=eio1_url,
            besluit=self.create_besluit(**{"besluittype": self.besluittype}),
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
        BesluitInformatieObjectFactory.create(
            informatieobject=eio2_url,
            besluit=self.create_besluit(**{"besluittype": BESLUITTYPE_EXTERNAL}),
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
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        self.create_zaak_besluit_services()
        bio1 = BesluitInformatieObjectFactory.create(
            informatieobject=eio1_url,
            besluit=self.create_besluit(**{"besluittype": self.besluittype}),
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
        bio2 = BesluitInformatieObjectFactory.create(
            informatieobject=eio2_url,
            besluit=self.create_besluit(**{"besluittype": BESLUITTYPE_EXTERNAL}),
        )

        url1 = reverse(bio1)
        url2 = reverse(bio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalBesluittypeScopeCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    besluittype = BESLUITTYPE_EXTERNAL
    component = ComponentTypes.brc

    def test_bio_list(self):
        url = reverse(BesluitInformatieObject)
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        self.create_zaak_besluit_services()
        bio1 = BesluitInformatieObjectFactory.create(
            informatieobject=eio1_url,
            besluit=self.create_besluit(**{"besluittype": self.besluittype}),
        )
        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
        BesluitInformatieObjectFactory.create(
            informatieobject=eio2_url,
            besluit=self.create_besluit(
                **{"besluittype": "https://externe.catalogus.nl/api/v1/besluiten/1"}
            ),
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
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        self.create_zaak_besluit_services()
        bio1 = BesluitInformatieObjectFactory.create(
            informatieobject=eio1_url,
            besluit=self.create_besluit(**{"besluittype": self.besluittype}),
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
        bio2 = BesluitInformatieObjectFactory.create(
            informatieobject=eio2_url,
            besluit=self.create_besluit(
                **{"besluittype": "https://externe.catalogus.nl/api/v1/besluiten/1"}
            ),
        )

        url1 = reverse(bio1)
        url2 = reverse(bio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.data)
        self.assertEqual(
            response2.status_code, status.HTTP_403_FORBIDDEN, response2.data
        )
