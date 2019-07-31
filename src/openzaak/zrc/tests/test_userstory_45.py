"""
Als KCC medewerker wil ik een behandelaar kunnen toewijzen zodat de melding
kan worden gerouteerd.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/45
"""
import uuid
from unittest.mock import patch

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolOmschrijving, RolTypes
from vng_api_common.tests import (
    JWTAuthMixin, TypeCheckMixin, get_operation_url
)
from zds_client.tests.mocks import mock_client

from zrc.api.scopes import SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
from zrc.datamodel.tests.factories import RolFactory, ZaakFactory

WATERNET = f'https://waternet.nl/api/organisatorische-eenheid/{uuid.uuid4().hex}'
ZAAKTYPE = f'https://example.com/api/v1/zaaktype/{uuid.uuid4().hex}'
ROLTYPE = "https://ztc.nl/roltypen/123"
ROLTYPE2 = "https://ztc.nl/roltypen/456"
ROLTYPE3 = "https://ztc.nl/roltypen/789"

ROLTYPE_RESPONSE = {
    "url": ROLTYPE,
    "zaaktype": ZAAKTYPE,
    "omschrijving": RolOmschrijving.behandelaar,
    "omschrijvingGeneriek": RolOmschrijving.behandelaar,
}

ROLTYPE2_RESPONSE = {
    "url": ROLTYPE2,
    "zaaktype": ZAAKTYPE,
    "omschrijving": RolOmschrijving.initiator,
    "omschrijvingGeneriek": RolOmschrijving.initiator,
}

ROLTYPE3_RESPONSE = {
    "url": ROLTYPE3,
    "zaaktype": ZAAKTYPE,
    "omschrijving": RolOmschrijving.zaakcoordinator,
    "omschrijvingGeneriek": RolOmschrijving.zaakcoordinator,
}


class US45TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @freeze_time('2018-01-01')
    def test_zet_behandelaar(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        url = get_operation_url('rol_create')

        with requests_mock.Mocker() as m:
            m.get(ROLTYPE, json=ROLTYPE_RESPONSE)

            with mock_client({ROLTYPE: ROLTYPE_RESPONSE}):
                response = self.client.post(url, {
                    'zaak': zaak_url,
                    'betrokkene': WATERNET,
                    'betrokkeneType': RolTypes.organisatorische_eenheid,
                    'roltype': ROLTYPE,
                    'roltoelichting': 'Verantwoordelijke behandelaar voor de melding',
                })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        response_data = response.json()

        self.assertIn('url', response_data)
        del response_data['url']
        del response_data['uuid']
        self.assertEqual(response_data, {
            'zaak': f'http://testserver{zaak_url}',
            'betrokkene': WATERNET,
            'betrokkeneType': RolTypes.organisatorische_eenheid,
            'roltype': ROLTYPE,
            'omschrijving': RolOmschrijving.behandelaar,
            'omschrijvingGeneriek': RolOmschrijving.behandelaar,
            'roltoelichting': 'Verantwoordelijke behandelaar voor de melding',
            'registratiedatum': '2018-01-01T00:00:00Z',
            'indicatieMachtiging': '',
            'betrokkeneIdentificatie': None
        })

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_meerdere_initiatoren_verboden(self, *mocks):
        """
        Uit RGBZ 2.0, deel 2, Attribuutsoort Rolomschrijving (bij relatieklasse
        ROL):

        Bij een ZAAK kan maximaal één ROL met als Rolomschrijving generiek
        'Initiator' voor komen.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving=RolOmschrijving.initiator,
            omschrijving_generiek=RolOmschrijving.initiator
        )
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        url = get_operation_url('rol_create')

        with requests_mock.Mocker() as m:
            m.get(ROLTYPE2, json=ROLTYPE2_RESPONSE)
            with mock_client({ROLTYPE2: ROLTYPE2_RESPONSE}):
                response = self.client.post(url, {
                    'zaak': zaak_url,
                    'betrokkene': WATERNET,
                    'betrokkeneType': RolTypes.organisatorische_eenheid,
                    'roltype': ROLTYPE2,
                    'roltoelichting': 'Melder',
                })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_meerdere_coordinatoren_verboden(self, *mocks):
        """
        Uit RGBZ 2.0, deel 2, Attribuutsoort Rolomschrijving (bij relatieklasse
        ROL):

        Bij een ZAAK kan maximaal één ROL met als Rolomschrijving generiek
        'Initiator' voor komen.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving=RolOmschrijving.zaakcoordinator,
            omschrijving_generiek=RolOmschrijving.zaakcoordinator,
        )
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        url = get_operation_url('rol_create')

        with requests_mock.Mocker() as m:
            m.get(ROLTYPE3, json=ROLTYPE3_RESPONSE)
            with mock_client({ROLTYPE3: ROLTYPE3_RESPONSE}):
                response = self.client.post(url, {
                    'zaak': zaak_url,
                    'betrokkene': WATERNET,
                    'betrokkeneType': RolTypes.organisatorische_eenheid,
                    'roltype': ROLTYPE3,
                    'roltoelichting': 'Melder',
                })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
