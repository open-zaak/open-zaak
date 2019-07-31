"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""
import uuid
from datetime import date
from unittest.mock import patch

from django.test import override_settings

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    RolOmschrijving, VertrouwelijkheidsAanduiding, ZaakobjectTypes
)
from vng_api_common.tests import (
    JWTAuthMixin, get_operation_url, get_validation_errors
)
from zds_client.tests.mocks import mock_client

from zrc.api.scopes import SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
from zrc.datamodel.models import KlantContact, Rol, Status, Zaak, ZaakObject
from zrc.datamodel.tests.factories import ZaakFactory

from .utils import ZAAK_WRITE_KWARGS, isodatetime

ZAAKTYPE = f'https://example.com/ztc/api/v1/catalogus/{uuid.uuid4().hex}/zaaktypen/{uuid.uuid4().hex}'
STATUS_TYPE = f'https://example.com/ztc/api/v1/catalogus/{uuid.uuid4().hex}/zaaktypen/{uuid.uuid4().hex}/statustypen/{uuid.uuid4().hex}'  # noqa
STATUS_TYPE_OVERLAST_GECONSTATEERD = f'https://example.com/ztc/api/v1/catalogus/{uuid.uuid4().hex}/zaaktypen/{uuid.uuid4().hex}/statustypen/{uuid.uuid4().hex}'  # noqa
VERANTWOORDELIJKE_ORGANISATIE = '517439943'
OBJECT_MET_ADRES = f'https://example.com/orc/api/v1/objecten/{uuid.uuid4().hex}'
FOTO = f'https://example.com/drc/api/v1/enkelvoudiginformatieobjecten/{uuid.uuid4().hex}'
# file:///home/bbt/Downloads/2a.aansluitspecificatieskennisgevingen-gegevenswoordenboek-entiteitenv1.0.6.pdf
# Stadsdeel is een WijkObject in het RSGB
STADSDEEL = f'https://example.com/rsgb/api/v1/wijkobjecten/{uuid.uuid4().hex}'

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

@patch("vng_api_common.validators.fetcher")
@patch("vng_api_common.validators.obj_has_shape", return_value=True)
@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class US39TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = ZAAKTYPE

    def test_create_zaak(self, *mocks):
        """
        Maak een zaak van een bepaald type.
        """
        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
            'toelichting': 'Een stel dronken toeristen speelt versterkte '
                           'muziek af vanuit een gehuurde boot.',
            'zaakgeometrie': {
                'type': 'Point',
                'coordinates': [
                    4.910649523925713,
                    52.37240093589432
                ]
            }
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()
        self.assertIn('identificatie', data)

        # verify that the identification has been generated
        self.assertIsInstance(data['identificatie'], str)
        self.assertNotEqual(data['identificatie'], '')
        self.assertIsInstance(data['zaakgeometrie'], dict)  # geojson object

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.zaaktype, ZAAKTYPE)
        self.assertEqual(zaak.registratiedatum, date(2018, 6, 11))
        self.assertEqual(
            zaak.toelichting,
            'Een stel dronken toeristen speelt versterkte '
            'muziek af vanuit een gehuurde boot.'
        )
        self.assertEqual(zaak.zaakgeometrie.x, 4.910649523925713)
        self.assertEqual(zaak.zaakgeometrie.y, 52.37240093589432)

    def test_create_zaak_zonder_bronorganisatie(self, *mocks):
        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'registratiedatum': '2018-06-11',
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'bronorganisatie')
        self.assertEqual(error['code'], 'required')

    def test_create_zaak_invalide_rsin(self, *mocks):
        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'bronorganisatie': '123456789',
            'registratiedatum': '2018-06-11',
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'bronorganisatie')
        self.assertEqual(error['code'], 'invalid')

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_zet_zaakstatus(self, *mocks):
        """
        De actuele status van een zaak moet gezet worden bij het aanmaken
        van de zaak.
        """
        url = get_operation_url('status_create')
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'statustype': STATUS_TYPE,
            'datumStatusGezet': isodatetime(2018, 6, 6, 17, 23, 43),
        }

        with mock_client(STATUSTYPE_RESPONSE):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        status_ = Status.objects.get()
        self.assertEqual(status_.zaak, zaak)
        detail_url = get_operation_url('status_read', uuid=status_.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(status_.uuid),
                'zaak': f"http://testserver{zaak_url}",
                'statustype': STATUS_TYPE,
                'datumStatusGezet': '2018-06-06T17:23:43Z',  # UTC
                'statustoelichting': '',
            }
        )

    def test_zet_adres_binnenland(self, *mocks):
        """
        Het adres van de melding moet in de zaak beschikbaar zijn.
        """
        url = get_operation_url('zaakobject_create')
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'object': OBJECT_MET_ADRES,
            'objectType': ZaakobjectTypes.adres,
            'relatieomschrijving': 'Het adres waar de overlast vastgesteld werd.',
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak, zaak)
        detail_url = get_operation_url('zaakobject_read', uuid=zaakobject.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(zaakobject.uuid),
                'zaak': f"http://testserver{zaak_url}",
                'object': OBJECT_MET_ADRES,
                'objectIdentificatie': None,
                'objectType': ZaakobjectTypes.adres,
                'objectTypeOverige': '',
                'relatieomschrijving': 'Het adres waar de overlast vastgesteld werd.',
            }
        )

    def test_create_klantcontact(self, *mocks):
        url = get_operation_url('klantcontact_create')
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'datumtijd': isodatetime(2018, 6, 11, 13, 47, 55),
            'kanaal': 'Webformulier',
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        klantcontact = KlantContact.objects.get()
        self.assertIsInstance(klantcontact.identificatie, str)
        self.assertNotEqual(klantcontact.identificatie, '')
        self.assertEqual(klantcontact.zaak, zaak)
        detail_url = get_operation_url('klantcontact_read', uuid=klantcontact.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(klantcontact.uuid),
                'zaak': f"http://testserver{zaak_url}",
                'identificatie': klantcontact.identificatie,
                'datumtijd': '2018-06-11T13:47:55Z',
                'kanaal': 'Webformulier',
            }
        )

    def test_zet_stadsdeel(self, *mocks):
        url = get_operation_url('zaakobject_create')
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'object': STADSDEEL,
            'objectType': ZaakobjectTypes.adres,
            'relatieomschrijving': 'Afgeleid gebied',
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak, zaak)
        detail_url = get_operation_url('zaakobject_read', uuid=zaakobject.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(zaakobject.uuid),
                'zaak': f"http://testserver{zaak_url}",
                'object': STADSDEEL,
                'objectIdentificatie': None,
                'objectType': ZaakobjectTypes.adres,
                'objectTypeOverige': '',
                'relatieomschrijving': 'Afgeleid gebied',
            }
        )

    @freeze_time('2018-01-01')
    def test_zet_verantwoordelijk(self, *mocks):
        url = get_operation_url('rol_create')
        betrokkene = f'https://example.com/orc/api/v1/vestigingen/waternet/{uuid.uuid4().hex}'
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'betrokkene': betrokkene,
            'betrokkeneType': 'vestiging',
            'roltype': ROLTYPE,
            'roltoelichting': 'Baggeren van gracht',
        }

        with requests_mock.Mocker() as m:
            m.get(ROLTYPE, json=ROLTYPE_RESPONSE)

            with mock_client({ROLTYPE: ROLTYPE_RESPONSE}):
                response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        rol = Rol.objects.get()
        self.assertEqual(rol.zaak, zaak)
        self.assertEqual(rol.betrokkene, betrokkene)
        detail_url = get_operation_url('rol_read', uuid=rol.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(rol.uuid),
                'zaak': f"http://testserver{zaak_url}",
                'betrokkene': betrokkene,
                'betrokkeneType': 'vestiging',
                'roltype': ROLTYPE,
                'omschrijving': RolOmschrijving.behandelaar,
                'omschrijvingGeneriek': RolOmschrijving.behandelaar,
                'roltoelichting': 'Baggeren van gracht',
                'registratiedatum': '2018-01-01T00:00:00Z',
                'indicatieMachtiging': '',
                'betrokkeneIdentificatie': None
            }
        )
