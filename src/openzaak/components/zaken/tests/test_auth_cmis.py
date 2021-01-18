# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN
from ..models import ZaakInformatieObject
from .factories import ZaakInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakinformatieobject_limited_to_authorized_zaken(self):
        self.create_zaak_besluit_services()
        zaak1 = self.create_zaak(
            **{
                "zaaktype": self.zaaktype,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            }
        )
        zaak2 = self.create_zaak(
            **{"vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar}
        )
        zaak3 = self.create_zaak(
            **{
                "zaaktype": self.zaaktype,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            }
        )
        # must show up
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))

        zio1 = ZaakInformatieObjectFactory.create(informatieobject=eio_url, zaak=zaak1,)
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url, zaak=zaak2,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url, zaak=zaak3,
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalZaaktypeScopeCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    component = ComponentTypes.zrc

    def test_zaakinformatieobject_list(self):
        self.create_zaak_besluit_services(
            base_zaaktype="https://externe.catalogus.nl/api/v1/"
        )
        zaak1 = self.create_zaak(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = self.create_zaak(
            zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))

        # must show up
        zio1 = ZaakInformatieObjectFactory.create(informatieobject=eio_url, zaak=zaak1,)
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url, zaak=zaak2,
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")

    def test_zaakinformatieobject_retrieve(self):
        self.create_zaak_besluit_services(
            base_zaaktype="https://externe.catalogus.nl/api/v1/"
        )
        zaak1 = self.create_zaak(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = self.create_zaak(
            zaaktype="https://externe.catalogus.nl/api/v1/zaaktypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        self.adapter.get(eio1_url, json=serialise_eio(eio1, eio1_url))
        zio1 = ZaakInformatieObjectFactory.create(
            informatieobject=eio1_url, zaak=zaak1,
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        self.adapter.get(eio2_url, json=serialise_eio(eio2, eio2_url))
        zio2 = ZaakInformatieObjectFactory.create(
            informatieobject=eio2_url, zaak=zaak2,
        )
        url1 = reverse(zio1)
        url2 = reverse(zio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
