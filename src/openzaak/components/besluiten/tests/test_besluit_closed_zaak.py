# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from django.test import override_settings
from django.utils import timezone
from django.utils.translation import gettext as _

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import (
    ComponentTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.besluiten.api.scopes import SCOPE_BESLUITEN_AANMAKEN
from openzaak.components.besluiten.constants import VervalRedenen
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
)
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class BesluitClosedZaakTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("besluit-list")
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim

    @classmethod
    def setUpTestData(cls):
        cls.besluittype = BesluitTypeFactory.create(concept=False)
        cls.besluittype_url = cls.check_for_instance(cls.besluittype)

        super().setUpTestData()

    def _add_besluiten_auth(self, besluittype=None, zaaktype=None):
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=[SCOPE_BESLUITEN_AANMAKEN],
            zaaktype=zaaktype if zaaktype else "",
            besluittype=self.besluittype_url if besluittype is None else besluittype,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def _add_zaken_auth(self, zaaktype=None, scopes=None):
        if scopes is None:
            scopes = []

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=scopes,
            zaaktype=zaaktype if zaaktype else "",
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def _add_catalogi_auth(self, component: ComponentTypes, catalogus, scopes):
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=component,
            scopes=scopes,
            catalogus=catalogus,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def setUp(self):
        super().setUp()

        self.content = {
            "verantwoordelijke_organisatie": "517439943",
            "identificatie": "123123",
            "besluittype": self.besluittype_url,
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

    def test_register_with_closed_zaak(self):
        self._add_besluiten_auth()

        zaak = ZaakFactory.create(
            einddatum=timezone.now(), zaaktype__catalogus=self.besluittype.catalogus
        )
        zaak_url = reverse(zaak)
        self.besluittype.zaaktypen.add(zaak.zaaktype)

        self.assertTrue(zaak.is_closed)

        content = self.content.copy()
        content["zaak"] = f"http://testserver{zaak_url}"

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(
            response.data["detail"],
            _("Je mag geen gegevens aanpassen van een gesloten zaak."),
        )

    def test_register_with_closed_zaak_with_force_scope(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(), zaaktype__catalogus=self.besluittype.catalogus
        )
        zaak_url = reverse(zaak)
        self.besluittype.zaaktypen.add(zaak.zaaktype)

        self.assertTrue(zaak.is_closed)

        self._add_besluiten_auth(
            besluittype=self.besluittype_url,
            zaaktype=f"http://testserver{reverse(zaak.zaaktype)}",
        )

        self._add_zaken_auth(
            scopes=[SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN],
            zaaktype=f"http://testserver{reverse(zaak.zaaktype)}",
        )

        content = self.content.copy()
        content["zaak"] = f"http://testserver{zaak_url}"

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_with_closed_zaak_with_force_scope_on_catalogus(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(),
            zaaktype__catalogus=self.besluittype.catalogus,
        )
        zaak_url = reverse(zaak)
        self.besluittype.zaaktypen.add(zaak.zaaktype)

        self.assertTrue(zaak.is_closed)

        self._add_besluiten_auth(
            besluittype=self.besluittype_url,
            zaaktype=f"http://testserver{reverse(zaak.zaaktype)}",
        )

        self._add_catalogi_auth(
            catalogus=self.besluittype.catalogus,
            scopes=[SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN],
            component=ComponentTypes.zrc,
        )

        content = self.content.copy()
        content["zaak"] = f"http://testserver{zaak_url}"

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
