"""
Als gemeente wil ik dat de aanvraag tbh een straatoptreden als zaak wordt
gecreëerd zodat mijn dossiervorming op orde is en de voortgang transparant is.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/163

Zie ook: test_userstory_39.py, test_userstory_169.py
"""
import datetime
import uuid
from unittest.mock import patch

from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    RolOmschrijving, RolTypes, VertrouwelijkheidsAanduiding, ZaakobjectTypes
)
from vng_api_common.tests import JWTAuthMixin, get_operation_url
from zds_client.tests.mocks import mock_client

from zrc.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
)
# aanvraag aangemaakt in extern systeem, leeft buiten ZRC
from zrc.datamodel.models import Zaak
from zrc.datamodel.tests.factories import ZaakFactory

from .utils import ZAAK_WRITE_KWARGS, parse_isodatetime

CATALOGUS = f'https://example.com/ztc/api/v1/catalogus/{uuid.uuid4().hex}'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
STATUS_TYPE = f'{ZAAKTYPE}/statustypen/1'

VERANTWOORDELIJKE_ORGANISATIE = '517439943'
AVG_INZAGE_VERZOEK = f'https://www.example.com/orc/api/v1/avg/inzageverzoeken/{uuid.uuid4().hex}'
BEHANDELAAR = f'https://www.example.com/orc/api/v1/brp/natuurlijkepersonen/{uuid.uuid4().hex}'

ROLTYPE = "https://ztc.nl/roltypen/123"

ROLTYPE_RESPONSE = {
    "url": ROLTYPE,
    "zaaktype": ZAAKTYPE,
    "omschrijving": RolOmschrijving.behandelaar,
    "omschrijvingGeneriek": RolOmschrijving.behandelaar,
}

STATUSTYPE_RESPONSE = {
    STATUS_TYPE: {
        'url': STATUS_TYPE,
        'zaaktype': ZAAKTYPE,
        'volgnummer': 1,
        'isEindstatus': False
    }
}


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class US153TestCase(JWTAuthMixin, APITestCase):

    scopes = [
        SCOPE_ZAKEN_CREATE,
        SCOPE_ZAKEN_ALLES_LEZEN,
        SCOPE_ZAKEN_BIJWERKEN
    ]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_zaak_with_kenmerken(self, *mocks):
        zaak_create_url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'identificatie': 'AVG-inzageverzoek-1',
            'omschrijving': 'Dagontheffing - Station Haarlem',
            'toelichting': 'Het betreft een clown met grote trom, mondharmonica en cymbalen.',
            'startdatum': '2018-08-15',
            'kenmerken': [{
                'kenmerk': 'kenmerk 1',
                'bron': 'bron 1',
            }, {
                'kenmerk': 'kenmerk 2',
                'bron': 'bron 2',
            }]
        }

        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get(identificatie=data['identificatie'])
        self.assertEqual(zaak.zaakkenmerk_set.count(), 2)

    def test_read_zaak_with_kenmerken(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak.zaakkenmerk_set.create(kenmerk='kenmerk 1', bron='bron 1')
        self.assertEqual(zaak.zaakkenmerk_set.count(), 1)

        zaak_read_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        response = self.client.get(zaak_read_url, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()

        self.assertTrue('kenmerken' in data)
        self.assertEqual(len(data['kenmerken']), 1)
        self.assertDictEqual(
            data['kenmerken'][0],
            {
                'kenmerk': 'kenmerk 1',
                'bron': 'bron 1',
            }
        )

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_zaak_with_kenmerken(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        kenmerk_1 = zaak.zaakkenmerk_set.create(kenmerk='kenmerk 1', bron='bron 1')
        self.assertEqual(zaak.zaakkenmerk_set.count(), 1)

        zaak_read_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        response = self.client.get(zaak_read_url, **ZAAK_WRITE_KWARGS)

        data = response.json()

        zaak_update_url = get_operation_url('zaak_update', uuid=zaak.uuid)
        data['kenmerken'].append({
            'kenmerk': 'kenmerk 2',
            'bron': 'bron 2',
        })
        data['verlenging'] = None
        data['opschorting'] = None

        response = self.client.put(zaak_update_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        zaak = Zaak.objects.get(identificatie=zaak.identificatie)
        self.assertEqual(zaak.zaakkenmerk_set.count(), 2)

        # All objects are deleted, and (re)created.
        self.assertFalse(kenmerk_1.pk in zaak.zaakkenmerk_set.values_list('pk', flat=True))

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @override_settings(
        ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
    )
    def test_full_flow(self, *mocks):
        zaak_create_url = get_operation_url('zaak_create')
        zaakobject_create_url = get_operation_url('zaakobject_create')
        status_create_url = get_operation_url('status_create')
        rol_create_url = get_operation_url('rol_create')

        # Creeer InzageVerzoek
        # self.client.post(...)

        # Creeer Zaak
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'identificatie': 'AVG-inzageverzoek-1',
            'omschrijving': 'Melding binnengekomen via website.',
            'toelichting': 'Vanuit melding: Beste,\n\nGraag zou ik ...',
            'startdatum': '2018-08-22',
            'kenmerken': [{
                'kenmerk': 'kenmerk 1',
                'bron': 'bron 1',
            }, {
                'kenmerk': 'kenmerk 2',
                'bron': 'bron 2',
            }]
        }
        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = response.json()

        # Koppel Zaak aan InzageVerzoek
        data = {
            'zaak': zaak['url'],
            'object': AVG_INZAGE_VERZOEK,
            'relatieomschrijving': 'Inzage verzoek horend bij deze zaak.',
            'objectType': ZaakobjectTypes.adres
        }
        response = self.client.post(zaakobject_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Geef de Zaak een initiele Status
        data = {
            'zaak': zaak['url'],
            'statustype': STATUS_TYPE,
            'datumStatusGezet': datetime.datetime.now().isoformat(),
        }

        with mock_client(STATUSTYPE_RESPONSE):
            response = self.client.post(status_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Haal mogelijke rollen op uit ZTC...
        # self.client.get(...)

        # Voeg een behandelaar toe.
        data = {
            'zaak': zaak['url'],
            'betrokkene': BEHANDELAAR,
            'betrokkeneType': RolTypes.natuurlijk_persoon,
            'roltype': ROLTYPE,
            'roltoelichting': 'Initiele behandelaar die meerdere (deel)behandelaren kan aanwijzen.'
        }
        with requests_mock.Mocker() as m:
            m.get(ROLTYPE, json=ROLTYPE_RESPONSE)
            with mock_client({ROLTYPE: ROLTYPE_RESPONSE}):
                response = self.client.post(rol_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Status wijzigingen...

        # Update Zaak met nieuwe behandeltermijn, uitstel van 2 weken.
        zaak_update_url = get_operation_url('zaak_update', uuid=zaak['url'].rsplit('/', 1)[1])

        if zaak['einddatumGepland']:
            end_date_planned = parse_isodatetime(zaak['einddatumGepland'])
        else:
            end_date_planned = datetime.datetime.now()

        data = zaak.copy()
        data['verlenging'] = None
        data['opschorting'] = None
        data['einddatumGepland'] = (end_date_planned + datetime.timedelta(days=14)).strftime('%Y-%m-%d')

        response = self.client.put(zaak_update_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # Voeg documenten toe...
        # self.client.post(...)
        # Koppel documenten aan Zaak
        # self.client.post(...)
