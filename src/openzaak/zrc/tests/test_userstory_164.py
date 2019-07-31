"""
Als straatartiest wil ik dat mijn aanvraag een uniek volgnummer krijgt zodat
ik in mijn communicatie snel kan verwijzen naar mijn aanvraag.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/164
"""
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import (
    JWTAuthMixin, get_operation_url, get_validation_errors
)

from zrc.api.scopes import SCOPE_ZAKEN_CREATE
from zrc.datamodel.models import Zaak
from zrc.datamodel.tests.factories import ZaakFactory

from .utils import ZAAK_WRITE_KWARGS

CATALOGUS = 'https://example.com/ztc/api/v1/catalogus/878a3318-5950-4642-8715-189745f91b04'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
VERANTWOORDELIJKE_ORGANISATIE = '517439943'


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class US164TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_geef_zelf_identificatie(self, *mocks):
        """
        Garandeer dat de client zelf een identificatie kan genereren.
        """
        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'identificatie': 'strtmzk-0001',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'bronorganisatie': '517439943',
            'startdatum': '2018-06-11',
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, 'strtmzk-0001')

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_uniqueness_identificatie(self, *mocks):
        ZaakFactory.create(identificatie='strtmzk-0001', bronorganisatie='517439943')

        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'identificatie': 'strtmzk-0001',
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'startdatum': '2018-06-11',
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 'invalid')

        error = get_validation_errors(response, 'identificatie')
        self.assertEqual(error['code'], 'identificatie-niet-uniek')
