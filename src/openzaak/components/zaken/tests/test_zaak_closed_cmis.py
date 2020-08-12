# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from ..models import ZaakInformatieObject
from .assertions import CRUDAssertions
from .factories import ZaakInformatieObjectFactory


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
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def test_zaakinformatieobjecten(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(closed=True)
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.get(io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.get(io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobject__informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateBlocked(
            reverse(ZaakInformatieObject),
            {"zaak": reverse(zaak), "informatieobject": io1_url,},
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
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    # FIXME
    def test_zaakinformatieobjecten(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(closed=True)
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.get(io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.get(io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=zaak.zaaktype,
            informatieobject__informatieobjecttype__catalogus=zaak.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateAllowed(
            reverse(ZaakInformatieObject),
            {"zaak": reverse(zaak), "informatieobject": io1_url,},
        )
        self.assertUpdateAllowed(zio_url)
        self.assertPartialUpdateAllowed(zio_url)
        self.assertDestroyAllowed(zio_url)
