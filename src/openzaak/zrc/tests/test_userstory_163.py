"""
Als gemeente wil ik dat de aanvraag tbh een straatoptreden als zaak wordt
gecreëerd zodat mijn dossiervorming op orde is en de voortgang transparant is.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/163

Zie ook: test_userstory_39.py, test_userstory_169.py
"""
from datetime import date
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import JWTAuthMixin, get_operation_url

from zrc.api.scopes import SCOPE_ZAKEN_CREATE

from .utils import ZAAK_WRITE_KWARGS

# aanvraag aangemaakt in extern systeem, leeft buiten ZRC
AANVRAAG = 'https://example.com/orc/api/v1/straatartiesten/37c60cda-689e-4e4a-969c-fa4ed56cb2c6'
CATALOGUS = 'https://example.com/ztc/api/v1/catalogus/878a3318-5950-4642-8715-189745f91b04'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
VERANTWOORDELIJKE_ORGANISATIE = '517439943'


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class US169TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_aanvraag(self, *mocks):
        """
        Maak een zaak voor een aanvraag.
        """
        zaak_create_url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'identificatie': 'HLM-straatartiest-42',
            'omschrijving': 'Dagontheffing - Station Haarlem',
            'toelichting': 'Het betreft een clown met grote trom, mondharmonica en cymbalen.',
            'startdatum': '2018-08-15',
        }

        # aanmaken zaak
        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()
        self.assertIn('identificatie', data)
        self.assertEqual(data['registratiedatum'], date.today().strftime('%Y-%m-%d'))
        self.assertEqual(data['startdatum'], '2018-08-15')
