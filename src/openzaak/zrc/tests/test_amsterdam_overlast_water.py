from unittest.mock import patch

from django.test import override_settings

from dateutil import parser
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie, BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding
)
from vng_api_common.tests import JWTAuthMixin, get_operation_url
from zds_client.tests.mocks import mock_client

from zrc.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
)
from zrc.datamodel.models import Zaak

from .test_userstory_52 import EIGENSCHAP_NAAM_BOOT, EIGENSCHAP_OBJECTTYPE
from .utils import ZAAK_WRITE_KWARGS, utcdatetime

VERANTWOORDELIJKE_ORGANISATIE = '517439943'
# ZTC
ZTC_ROOT = 'https://example.com/ztc/api/v1'
CATALOGUS = f'{ZTC_ROOT}/catalogus/878a3318-5950-4642-8715-189745f91b04'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
RESULTAATTYPE = f'{ZAAKTYPE}/resultaattypen/5b348dbf-9301-410b-be9e-83723e288785'
STATUSTYPE = f'{ZAAKTYPE}/statustypen/5b348dbf-9301-410b-be9e-83723e288785'
STATUSTYPE_OVERLAST_GECONSTATEERD = f'{ZAAKTYPE}/statustypen/b86aa339-151e-45f0-ad6c-20698f50b6cd'


TEST_DATA = {
    "id": 9966,
    "last_status": "o",
    "adres": "Oosterdok 51, 1011 Amsterdam, Netherlands",
    "datetime": "2018-05-28T09:05:08.732587+02:00",
    "text": "test",
    "waternet_soort_boot": "Nee",
    "waternet_rederij": "Onbekend",
    "waternet_naam_boot": "De Amsterdam",
    "datetime_overlast": "2018-05-28T08:35:11+02:00",
    "email": "",
    "phone_number": "",
    "source": "Telefoon 14020",
    "text_extra": "",
    "image": None,
    "main_category": "",
    "sub_category": "Geluid",
    "ml_cat": "melding openbare ruimte",
    "stadsdeel": "Centrum",
    "coordinates": "POINT (4.910649523925713 52.37240093589432)",
    "verantwoordelijk": "Waternet"
}


class Application:

    def __init__(self, client, data: dict):
        self.client = client

        self.data = data
        self.references = {}

    def store_notification(self):
        # registreer zaak & zet statussen, resultaat
        self.registreer_zaak()
        self.zet_statussen_resultaat()
        self.registreer_domein_data()
        self.registreer_klantcontact()

    def registreer_zaak(self):
        zaak_create_url = get_operation_url('zaak_create')

        created = parser.parse(self.data['datetime'])
        intern_id = self.data['id']

        response = self.client.post(zaak_create_url, {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'identificatie': f'WATER_{intern_id}',
            'registratiedatum': created.strftime('%Y-%m-%d'),
            'startdatum': created.strftime('%Y-%m-%d'),
            'toelichting': self.data['text'],
            'zaakgeometrie': self.data['coordinates'],
        }, **ZAAK_WRITE_KWARGS)

        self.references['zaak_url'] = response.json()['url']

    @override_settings(
        ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
    )
    def zet_statussen_resultaat(self):
        status_create_url = get_operation_url('status_create')
        resultaat_create_url = get_operation_url('resultaat_create')
        created = parser.parse(self.data['datetime'])

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
                    'datumkenmerk': None,
                    'objecttype': None,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: {
                'url': STATUSTYPE,
                'zaaktype': ZAAKTYPE,
                'volgnummer': 1,
                'isEindstatus': False,
            },
            STATUSTYPE_OVERLAST_GECONSTATEERD: {
                'url': STATUSTYPE_OVERLAST_GECONSTATEERD,
                'zaaktype': ZAAKTYPE,
                'volgnummer': 2,
                'isEindstatus': True,
            }
        }
        with mock_client(responses):
            self.client.post(status_create_url, {
                'zaak': self.references['zaak_url'],
                'statustype': STATUSTYPE,
                'datumStatusGezet': created.isoformat(),
            })

            self.client.post(resultaat_create_url, {
                'zaak': self.references['zaak_url'],
                'resultaattype': RESULTAATTYPE,
                'toelichting': '',
            })

            self.client.post(status_create_url, {
                'zaak': self.references['zaak_url'],
                'statustype': STATUSTYPE_OVERLAST_GECONSTATEERD,
                'datumStatusGezet': parser.parse(self.data['datetime_overlast']).isoformat(),
            })

    def registreer_domein_data(self):
        zaak_uuid = self.references['zaak_url'].rsplit('/')[-1]
        url = get_operation_url('zaakeigenschap_create', zaak_uuid=zaak_uuid)

        responses = {
            EIGENSCHAP_OBJECTTYPE: {
                'url': EIGENSCHAP_OBJECTTYPE,
                'naam': 'melding_type',
            },
            EIGENSCHAP_NAAM_BOOT: {
                'url': EIGENSCHAP_NAAM_BOOT,
                'naam': 'waternet_naam_boot',
            }
        }

        with mock_client(responses):
            self.client.post(url, {
                'zaak': self.references['zaak_url'],
                'eigenschap': EIGENSCHAP_OBJECTTYPE,
                'waarde': 'overlast_water',
            })
            self.client.post(url, {
                'zaak': self.references['zaak_url'],
                'eigenschap': EIGENSCHAP_NAAM_BOOT,
                'waarde': TEST_DATA['waternet_naam_boot'],
            })

    def registreer_klantcontact(self):
        url = get_operation_url('klantcontact_create')
        self.client.post(url, {
            'zaak': self.references['zaak_url'],
            'datumtijd': self.data['datetime'],
            'kanaal': self.data['source'],
        })


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class US39IntegrationTestCase(JWTAuthMixin, APITestCase):
    """
    Simulate a full realistic flow.
    """
    scopes = [
        SCOPE_ZAKEN_CREATE,
        SCOPE_STATUSSEN_TOEVOEGEN,
        SCOPE_ZAKEN_BIJWERKEN
    ]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_full_flow(self, *mocks):
        app = Application(self.client, TEST_DATA)

        app.store_notification()

        zaak = Zaak.objects.get(identificatie='WATER_9966')
        self.assertEqual(zaak.toelichting, 'test')
        self.assertEqual(zaak.zaakgeometrie.x, 4.910649523925713)
        self.assertEqual(zaak.zaakgeometrie.y, 52.37240093589432)

        self.assertEqual(zaak.status_set.count(), 2)

        last_status = zaak.status_set.order_by('-datum_status_gezet').first()
        self.assertEqual(last_status.statustype, STATUSTYPE)
        self.assertEqual(
            last_status.datum_status_gezet,
            utcdatetime(2018, 5, 28, 7, 5, 8, 732587),
        )

        first_status = zaak.status_set.order_by('datum_status_gezet').first()
        self.assertEqual(first_status.statustype, STATUSTYPE_OVERLAST_GECONSTATEERD)
        self.assertEqual(
            first_status.datum_status_gezet,
            utcdatetime(2018, 5, 28, 6, 35, 11)
        )

        klantcontact = zaak.klantcontact_set.get()
        self.assertEqual(klantcontact.kanaal, 'Telefoon 14020')
        self.assertEqual(
            klantcontact.datumtijd,
            utcdatetime(2018, 5, 28, 7, 5, 8, 732587),
        )

        eigenschappen = zaak.zaakeigenschap_set.all()
        self.assertEqual(eigenschappen.count(), 2)
        naam_boot = eigenschappen.get(eigenschap=EIGENSCHAP_NAAM_BOOT)
        self.assertEqual(naam_boot.waarde, 'De Amsterdam')
