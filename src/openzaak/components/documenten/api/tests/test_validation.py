from copy import deepcopy

from django.test import override_settings

from openzaak.components.documenten.models.constants import (
    OndertekeningSoorten, Statussen
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import (
    JWTAuthMixin, get_validation_errors, reverse, reverse_lazy
)
from vng_api_common.validators import URLValidator

INFORMATIEOBJECTTYPE = 'https://example.com/informatieobjecttype/foo'


class EnkelvoudigInformatieObjectTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def assertGegevensGroepRequired(self, url: str, field: str, base_body: dict, cases: tuple):
        for key, code in cases:
            with self.subTest(key=key, expected_code=code):
                body = deepcopy(base_body)
                del body[key]
                response = self.client.post(url, {field: body})

                error = get_validation_errors(response, f'{field}.{key}')
                self.assertEqual(error['code'], code)

    def assertGegevensGroepValidation(self, url: str, field: str, base_body: dict, cases: tuple):
        for key, code, blank_value in cases:
            with self.subTest(key=key, expected_code=code):
                body = deepcopy(base_body)
                body[key] = blank_value
                response = self.client.post(url, {field: body})

                error = get_validation_errors(response, f'{field}.{key}')
                self.assertEqual(error['code'], code)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_404')
    def test_validate_informatieobjecttype_invalid(self):
        url = reverse('enkelvoudiginformatieobject-list')

        response = self.client.post(url, {
            'informatieobjecttype': INFORMATIEOBJECTTYPE,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'informatieobjecttype')
        self.assertEqual(error['code'], URLValidator.code)

    def test_link_fetcher_cannot_connect(self):
        url = reverse('enkelvoudiginformatieobject-list')

        response = self.client.post(url, {
            'informatieobjecttype': 'http://invalid-host/informatieobjecttype/foo',
        })

        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_integriteit(self):
        url = reverse('enkelvoudiginformatieobject-list')

        base_body = {
            'algoritme': 'MD5',
            'waarde': 'foobarbaz',
            'datum': '2018-12-13',
        }

        cases = (
            ('algoritme', 'required'),
            ('waarde', 'required'),
            ('datum', 'required'),
        )

        self.assertGegevensGroepRequired(url, 'integriteit', base_body, cases)

    def test_integriteit_bad_values(self):
        url = reverse('enkelvoudiginformatieobject-list')

        base_body = {
            'algoritme': 'MD5',
            'waarde': 'foobarbaz',
            'datum': '2018-12-13',
        }

        cases = (
            ('algoritme', 'invalid_choice', ''),
            ('waarde', 'blank', ''),
            ('datum', 'null', None),
        )

        self.assertGegevensGroepValidation(url, 'integriteit', base_body, cases)

    def test_ondertekening(self):
        url = reverse('enkelvoudiginformatieobject-list')

        base_body = {
            'soort': OndertekeningSoorten.analoog,
            'datum': '2018-12-13',
        }

        cases = (
            ('soort', 'required'),
            ('datum', 'required'),
        )

        self.assertGegevensGroepRequired(url, 'ondertekening', base_body, cases)

    def test_ondertekening_bad_values(self):
        url = reverse('enkelvoudiginformatieobject-list')

        base_body = {
            'soort': OndertekeningSoorten.digitaal,
            'datum': '2018-12-13',
        }
        cases = (
            ('soort', 'invalid_choice', ''),
            ('datum', 'null', None),
        )

        self.assertGegevensGroepValidation(url, 'ondertekening', base_body, cases)


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class InformatieObjectStatusTests(JWTAuthMixin, APITestCase):

    url = reverse_lazy('enkelvoudiginformatieobject-list')
    heeft_alle_autorisaties = True

    def test_ontvangen_informatieobjecten(self):
        """
        Assert certain statuses are not allowed for received documents.

        RGBZ 2.00.02 deel II Concept 20180613: De waarden ?in bewerking?
        en ?ter vaststelling? zijn niet van toepassing op ontvangen
        informatieobjecten.
        """
        invalid_statuses = (Statussen.in_bewerking, Statussen.ter_vaststelling)
        data = {
            'bronorganisatie': '319582462',
            'creatiedatum': '2018-12-24',
            'titel': 'dummy',
            'auteur': 'dummy',
            'taal': 'nld',
            'inhoud': 'aGVsbG8gd29ybGQ=',
            'informatieobjecttype': INFORMATIEOBJECTTYPE,
            'ontvangstdatum': '2018-12-24',
        }

        for invalid_status in invalid_statuses:
            with self.subTest(status=invalid_status):
                _data = data.copy()
                _data['status'] = invalid_status

                response = self.client.post(self.url, _data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, 'status')
            self.assertEqual(error['code'], 'invalid_for_received')

    def test_informatieobjecten_niet_ontvangen(self):
        """
        All statusses should be allowed when the informatieobject doesn't have
        a receive date.
        """
        for valid_status, _ in Statussen.choices:
            with self.subTest(status=status):
                data = {
                    'ontvangstdatum': None,
                    'status': valid_status
                }

                response = self.client.post(self.url, data)

            error = get_validation_errors(response, 'status')
            self.assertIsNone(error)

    def test_status_set_ontvangstdatum_is_set_later(self):
        """
        Assert that setting the ontvangstdatum later, after an 'invalid' status
        has been set, is not possible.
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            ontvangstdatum=None,
            informatieobjecttype=INFORMATIEOBJECTTYPE
        )
        url = reverse('enkelvoudiginformatieobject-detail', kwargs={'uuid': eio.uuid})

        for invalid_status in (Statussen.in_bewerking, Statussen.ter_vaststelling):
            with self.subTest(status=invalid_status):
                eio.status = invalid_status
                eio.save()
                data = {'ontvangstdatum': '2018-12-24'}

                response = self.client.patch(url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                error = get_validation_errors(response, 'status')
                self.assertEqual(error['code'], 'invalid_for_received')


class FilterValidationTests(JWTAuthMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """
    heeft_alle_autorisaties = True

    def test_oio_invalid_filters(self):
        url = reverse('objectinformatieobject-list')

        invalid_filters = {
            'object': '123',  # must be url
            'informatieobject': '123',  # must be url
            'foo': 'bar',  # unknown
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value}, HTTP_ACCEPT_CRS='EPSG:4326')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
