# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als KCC medewerker wil ik een behandelaar kunnen toewijzen zodat de melding
kan worden gerouteerd.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/45
"""
import uuid

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolOmschrijving, RolTypes
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from .factories import RolFactory, ZaakFactory
from .utils import get_operation_url

WATERNET = f"https://waternet.nl/api/organisatorische-eenheid/{uuid.uuid4().hex}"


class US45TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2018-01-01")
    def test_zet_behandelaar(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(
            omschrijving=RolOmschrijving.behandelaar,
            omschrijving_generiek=RolOmschrijving.behandelaar,
            zaaktype=zaak.zaaktype,
        )
        roltype_url = reverse(roltype)
        url = get_operation_url("rol_create")

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "betrokkene": WATERNET,
                "betrokkeneType": RolTypes.organisatorische_eenheid,
                "roltype": f"http://testserver{roltype_url}",
                "roltoelichting": "Verantwoordelijke behandelaar voor de melding",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        response_data = response.json()

        self.assertIn("url", response_data)
        del response_data["url"]
        del response_data["uuid"]
        self.assertEqual(
            response_data,
            {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": WATERNET,
                "betrokkeneType": RolTypes.organisatorische_eenheid,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": RolOmschrijving.behandelaar,
                "omschrijvingGeneriek": RolOmschrijving.behandelaar,
                "roltoelichting": "Verantwoordelijke behandelaar voor de melding",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": None,
            },
        )

    def test_meerdere_initiatoren_verboden(self):
        """
        Uit RGBZ 2.0, deel 2, Attribuutsoort Rolomschrijving (bij relatieklasse
        ROL):

        Bij een ZAAK kan maximaal één ROL met als Rolomschrijving generiek
        'Initiator' voor komen.
        """
        zaak = ZaakFactory.create()
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving=RolOmschrijving.initiator,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        roltype = RolTypeFactory.create(
            omschrijving=RolOmschrijving.initiator,
            omschrijving_generiek=RolOmschrijving.initiator,
            zaaktype=zaak.zaaktype,
        )
        roltype_url = reverse(roltype)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("rol_create")

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "betrokkene": WATERNET,
                "betrokkeneType": RolTypes.organisatorische_eenheid,
                "roltype": roltype_url,
                "roltoelichting": "Melder",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_meerdere_coordinatoren_verboden(self):
        """
        Uit RGBZ 2.0, deel 2, Attribuutsoort Rolomschrijving (bij relatieklasse
        ROL):

        Bij een ZAAK kan maximaal één ROL met als Rolomschrijving generiek
        'Initiator' voor komen.
        """
        zaak = ZaakFactory.create()
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving=RolOmschrijving.zaakcoordinator,
            omschrijving_generiek=RolOmschrijving.zaakcoordinator,
        )
        roltype = RolTypeFactory.create(
            omschrijving=RolOmschrijving.zaakcoordinator,
            omschrijving_generiek=RolOmschrijving.zaakcoordinator,
            zaaktype=zaak.zaaktype,
        )
        roltype_url = reverse(roltype)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("rol_create")

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "betrokkene": WATERNET,
                "betrokkeneType": RolTypes.organisatorische_eenheid,
                "roltype": roltype_url,
                "roltoelichting": "Melder",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
