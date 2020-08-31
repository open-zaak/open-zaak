# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import mock_service_oas_get
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ...catalogi.tests.factories import ZaakTypeFactory
from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from ..models import ZaakInformatieObject
from .assertions import CRUDAssertions
from .factories import ZaakFactory, ZaakInformatieObjectFactory


@tag("closed-zaak", "cmis")
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataNotAllowedCMISTests(
    JWTAuthMixin, CRUDAssertions, APICMISTestCase, OioMixin
):
    """
    Test that updating/adding related data of a Zaak is not allowed when the Zaak is
    closed.
    """

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype, closed=True)

        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def _mock_zaak(self):
        mock_service_oas_get(self.adapter, APITypes.zrc, self.base_zaak)
        mock_service_oas_get(self.adapter, APITypes.ztc, self.base_zaaktype)

        self.adapter.get(
            make_absolute_uri(reverse(self.zaak)),
            json={
                "url": make_absolute_uri(reverse(self.zaak)),
                "identificatie": self.zaak.identificatie,
                "zaaktype": make_absolute_uri(reverse(self.zaak.zaaktype)),
            },
        )

        self.adapter.get(
            make_absolute_uri(reverse(self.zaak.zaaktype)),
            json={
                "url": make_absolute_uri(reverse(self.zaak.zaaktype)),
                "identificatie": self.zaak.zaaktype.identificatie,
                "omschrijving": "Melding Openbare Ruimte",
            },
        )

    def test_zaakinformatieobjecten(self):
        self.create_zaak_besluit_services()
        self._mock_zaak()
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.get(io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.get(io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobject__informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateBlocked(
            reverse(ZaakInformatieObject),
            {
                "zaak": f"http://testserver{reverse(self.zaak)}",
                "informatieobject": io1_url,
            },
        )
        self.assertUpdateBlocked(zio_url)
        self.assertPartialUpdateBlocked(zio_url)
        self.assertDestroyBlocked(zio_url)


@tag("closed-zaak", "cmis")
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataAllowedCMISTests(
    JWTAuthMixin, CRUDAssertions, APICMISTestCase, OioMixin
):
    """
    Test that updating/adding related data of a Zaak is not allowed when the Zaak is
    closed.
    """

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype, closed=True)

        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def _mock_zaak(self):
        mock_service_oas_get(self.adapter, APITypes.zrc, self.base_zaak)
        mock_service_oas_get(self.adapter, APITypes.ztc, self.base_zaaktype)

        self.adapter.get(
            make_absolute_uri(reverse(self.zaak)),
            json={
                "url": make_absolute_uri(reverse(self.zaak)),
                "identificatie": self.zaak.identificatie,
                "zaaktype": make_absolute_uri(reverse(self.zaak.zaaktype)),
            },
        )

        self.adapter.get(
            make_absolute_uri(reverse(self.zaak.zaaktype)),
            json={
                "url": make_absolute_uri(reverse(self.zaak.zaaktype)),
                "identificatie": self.zaak.zaaktype.identificatie,
                "omschrijving": "Melding Openbare Ruimte",
            },
        )

    def test_zaakinformatieobjecten(self):
        self.create_zaak_besluit_services()
        self._mock_zaak()
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.get(io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.get(io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=self.zaak.zaaktype,
            informatieobject__informatieobjecttype__catalogus=self.zaak.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateAllowed(
            reverse(ZaakInformatieObject),
            {
                "zaak": f"http://testserver{reverse(self.zaak)}",
                "informatieobject": io1_url,
            },
        )
        self.assertUpdateAllowed(zio_url)
        self.assertPartialUpdateAllowed(zio_url)
        self.assertDestroyAllowed(zio_url)
