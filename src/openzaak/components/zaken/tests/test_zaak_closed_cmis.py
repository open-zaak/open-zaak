# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test import mock_service_oas_get

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...catalogi.tests.factories import InformatieObjectTypeFactory, ZaakTypeFactory
from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from ..models import ZaakInformatieObject
from .assertions import CRUDAssertions
from .factories import ZaakFactory, ZaakInformatieObjectFactory


@tag("closed-zaak")
@require_cmis
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataNotAllowedCMISTests(
    JWTAuthMixin, CRUDAssertions, APICMISTestCase
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

    def _mock_zaak(self):
        mock_service_oas_get(self.adapter, self.base_zaak, APITypes.zrc)
        mock_service_oas_get(self.adapter, self.base_zaaktype, APITypes.ztc)

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
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.zaaktype.catalogus, zaaktypen__zaaktype=self.zaaktype
        )
        io1 = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iotype)
        io1_url = f"http://testserver{reverse(io1)}"

        io2 = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iotype)
        io2_url = f"http://testserver{reverse(io2)}"

        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject=io2_url,
        )
        zio_url = f"http://testserver{reverse(zio)}"

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


@tag("closed-zaak")
@require_cmis
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataAllowedCMISTests(
    JWTAuthMixin, CRUDAssertions, APICMISTestCase
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

    def test_zaakinformatieobjecten(self):
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.zaaktype.catalogus, zaaktypen__zaaktype=self.zaaktype
        )
        io1 = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iotype)
        io1_url = f"http://testserver{reverse(io1)}"

        io2 = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iotype)
        io2_url = f"http://testserver{reverse(io2)}"
        zio = ZaakInformatieObjectFactory(zaak=self.zaak, informatieobject=io2_url)
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
