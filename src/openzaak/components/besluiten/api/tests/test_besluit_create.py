from datetime import date
from unittest.mock import patch
from unittest import skip

from django.test import override_settings
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, TypeCheckMixin, reverse, get_validation_errors
from zds_client.tests.mocks import mock_client

from openzaak.components.besluiten.api.tests.mixins import MockSyncMixin
from openzaak.components.besluiten.api.tests.utils import get_operation_url
from openzaak.components.besluiten.models import Besluit
from openzaak.components.besluiten.models.constants import VervalRedenen
from openzaak.components.zaken.models.tests.factories import ZaakFactory
from openzaak.components.catalogi.models.tests.factories import BesluitTypeFactory

ZAAK = 'https://zrc.com/zaken/1234'
ZAAKTYPE = 'https://ztc.com/zaaktypen/1234'
INFORMATIEOBJECT = 'https://drc.com/api/v1/enkelvoudigeinformatieobjecten/1234'
INFORMATIEOBJECTTYPE = 'https://ztc.com/informatieobjecttypen/1234'
BESLUITTYPE = 'https://ztc.com/besluittypen/1234'

RESPONSES = {
    BESLUITTYPE: {
        'url': BESLUITTYPE,
        'zaaktypes': [
            ZAAKTYPE
        ]
    },
    ZAAK: {
        'url': ZAAK,
        'zaaktype': ZAAKTYPE
    },
    ZAAKTYPE: {
        'url': ZAAKTYPE,
        'informatieobjecttypen': [
            INFORMATIEOBJECTTYPE
        ]
    },
    INFORMATIEOBJECT: {
        'url': INFORMATIEOBJECT,
        'informatieobjecttype': INFORMATIEOBJECTTYPE
    }
}


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class BesluitCreateTests(MockSyncMixin, TypeCheckMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.besluit_list_url = get_operation_url('besluit_create')

    @freeze_time('2018-09-06T12:08+0200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_fk_remote(self, *mocks):
        with self.subTest(part='besluit_create'):
            # see https://github.com/VNG-Realisatie/gemma-zaken/issues/162#issuecomment-416598476
            with mock_client(RESPONSES):
                response = self.client.post(self.besluit_list_url, {
                    'verantwoordelijke_organisatie': '517439943',  # RSIN
                    'besluittype': BESLUITTYPE,
                    'zaak': ZAAK,
                    'datum': '2018-09-06',
                    'toelichting': "Vergunning verleend.",
                    'ingangsdatum': '2018-10-01',
                    'vervaldatum': '2018-11-01',
                    'vervalreden': VervalRedenen.tijdelijk,
                })

            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            self.assertResponseTypes(response.data, (
                ('url', str),
                ('identificatie', str),
                ('verantwoordelijke_organisatie', str),
                ('besluittype', str),
                ('zaak', str),
                ('datum', str),
                ('toelichting', str),
                ('bestuursorgaan', str),
                ('ingangsdatum', str),
                ('vervaldatum', str),
                ('vervalreden', str),
                ('publicatiedatum', type(None)),
                ('verzenddatum', type(None)),
                ('uiterlijke_reactiedatum', type(None)),
            ))

            self.assertEqual(Besluit.objects.count(), 1)

            besluit = Besluit.objects.get()
            self.assertEqual(besluit.verantwoordelijke_organisatie, '517439943')
            self.assertEqual(besluit.besluittype, 'https://ztc.com/besluittypen/1234')
            self.assertEqual(besluit.zaak, 'https://zrc.com/zaken/1234')
            self.assertEqual(
                besluit.datum,
                date(2018, 9, 6)
            )
            self.assertEqual(besluit.toelichting, "Vergunning verleend.")
            self.assertEqual(besluit.ingangsdatum, date(2018, 10, 1))
            self.assertEqual(besluit.vervaldatum, date(2018, 11, 1))
            self.assertEqual(besluit.vervalreden, VervalRedenen.tijdelijk)

        with self.subTest(part='besluitinformatieobject_create'):
            url = get_operation_url(
                'besluitinformatieobject_create'
            )

            with mock_client(RESPONSES):
                response = self.client.post(url, {
                    'besluit': reverse(besluit),
                    'informatieobject': 'https://drc.com/api/v1/enkelvoudigeinformatieobjecten/1234',
                })

            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            self.assertResponseTypes(response.data, (
                ('url', str),
                ('informatieobject', str),
            ))

            self.assertEqual(besluit.besluitinformatieobject_set.count(), 1)
            self.assertEqual(
                besluit.besluitinformatieobject_set.get().informatieobject,
                'https://drc.com/api/v1/enkelvoudigeinformatieobjecten/1234'
            )

    @skip('not implemented yet')
    def test_create_fk_remote_invalid_resource(self):
        response = self.client.post(self.besluit_list_url, {
            'verantwoordelijke_organisatie': '517439943',
            'besluittype': BESLUITTYPE,
            'zaak': ZAAK,
            'datum': '2018-09-06',
            'toelichting': "Vergunning verleend.",
            'ingangsdatum': '2018-10-01',
            'vervaldatum': '2018-11-01',
            'vervalreden': VervalRedenen.tijdelijk,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        validation_error = get_validation_errors(response, 'nonFieldErrors')

        self.assertEqual(validation_error['code'], 'invalid-betrokkene')

    def test_create_fk_local(self):
        zaak = ZaakFactory.create()
        besluittype = BesluitTypeFactory.create()
        zaak_url = reverse(zaak)
        besluittype_url = reverse(besluittype)

        data = {
            'verantwoordelijke_organisatie': '517439943',  # RSIN
            'besluittype': besluittype_url,
            'zaak': zaak_url,
            'datum': '2018-09-06',
            'toelichting': "Vergunning verleend.",
            'ingangsdatum': '2018-10-01',
            'vervaldatum': '2018-11-01',
            'vervalreden': VervalRedenen.tijdelijk,
        }

        response = self.client.post(self.besluit_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        besluit = Besluit.objects.get()

        self.assertEqual(besluit.verantwoordelijke_organisatie, '517439943')
        self.assertEqual(besluit.vervalreden, VervalRedenen.tijdelijk)
        self.assertEqual(besluit.besluittype, besluittype)
        self.assertEqual(besluit.zaak, zaak)

    @skip('not implemented yet')
    def test_create_fk_local_invalid_resource(self):
        zaak = ZaakFactory.create()
        besluittype = BesluitTypeFactory.create()
        zaak_url = reverse(zaak)[:-1]
        besluittype_url = reverse(besluittype)[:-1]

        data = {
            'verantwoordelijke_organisatie': '517439943',  # RSIN
            'besluittype': besluittype_url,
            'zaak': zaak_url,
            'datum': '2018-09-06',
            'toelichting': "Vergunning verleend.",
            'ingangsdatum': '2018-10-01',
            'vervaldatum': '2018-11-01',
            'vervalreden': VervalRedenen.tijdelijk,
        }

        response = self.client.post(self.besluit_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        validation_error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(validation_error['code'], 'invalid-betrokkene')

    @skip('not implemented yet')
    def test_create_not_unique(self):
        pass

    @skip('not implemented yet')
    def test_create_local_zaken_mismatch(self):
        pass

    @skip('not implemented yet')
    def test_create_local_catalogi_mismatch(self):
        pass

    @skip('not implemented yet')
    def test_create_local_zaken_catalogi_mismatch(self):
        pass
