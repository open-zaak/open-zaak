# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
from django.conf import settings
from django.test import override_settings, tag

from drc_cmis.models import CMISConfig, UrlMapping
from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN
from ..models import ZaakInformatieObject
from .factories import ZaakFactory, ZaakInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectCMISTests(JWTAuthMixin, APICMISTestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_list_zaakinformatieobject_limited_to_authorized_zaken(self):
        zaak1 = ZaakFactory.create(
            **{
                "zaaktype": self.zaaktype,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            }
        )
        zaak2 = ZaakFactory.create(
            **{"vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar}
        )
        zaak3 = ZaakFactory.create(
            **{
                "zaaktype": self.zaaktype,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            }
        )
        # must show up
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()

        zio1 = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            zaak=zaak1,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            zaak=zaak2,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            zaak=zaak3,
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")


@tag("external-urls")
@require_cmis
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalZaaktypeScopeCMISTests(JWTAuthMixin, APICMISTestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root="https://externe.catalogus.nl/api/v1/",
            label="external zaaktypen",
            auth_type=AuthTypes.no_auth,
        )

        if settings.CMIS_URL_MAPPING_ENABLED:
            config = CMISConfig.get_solo()

            UrlMapping.objects.create(
                long_pattern="https://externe.catalogus.nl",
                short_pattern="https://xcat.nl",
                config=config,
            )

    def test_zaakinformatieobject_list(self):
        self.another_zaaktype_url = "https://externe.catalogus.nl/api/v1/zaaktypen/1"

        self.adapter.get(
            self.zaaktype,
            json={
                "url": self.zaaktype,
                "identificatie": "ZAAKTYPE-01",
                "omschrijving": "Melding Openbare Ruimte",
            },
        )
        self.adapter.get(
            self.another_zaaktype_url,
            json={
                "url": self.another_zaaktype_url,
                "identificatie": "ZAAKTYPE-02",
                "omschrijving": "Melding Openbare Ruimte",
            },
        )

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()

        # must show up
        zio1 = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            zaak__zaaktype=self.another_zaaktype_url,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver{zaak_url}")

    def test_zaakinformatieobject_retrieve(self):
        self.another_zaaktype_url = "https://externe.catalogus.nl/api/v1/zaaktypen/1"

        self.adapter.get(
            self.zaaktype,
            json={
                "url": self.zaaktype,
                "identificatie": "ZAAKTYPE-01",
                "omschrijving": "Melding Openbare Ruimte",
            },
        )
        self.adapter.get(
            self.another_zaaktype_url,
            json={
                "url": self.another_zaaktype_url,
                "identificatie": "ZAAKTYPE-02",
                "omschrijving": "Melding Openbare Ruimte",
            },
        )
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        zio1 = ZaakInformatieObjectFactory.create(
            informatieobject=eio1_url,
            zaak__zaaktype=self.zaaktype,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = eio2.get_url()
        zio2 = ZaakInformatieObjectFactory.create(
            informatieobject=eio2_url,
            zaak__zaaktype=self.another_zaaktype_url,
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zio1)
        url2 = reverse(zio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
