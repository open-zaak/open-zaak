"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/345
"""
from datetime import date
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie, Archiefstatus, BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding
)
from vng_api_common.tests import JWTAuthMixin, get_operation_url
from zds_client.tests.mocks import mock_client

from zrc.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE,
    SCOPEN_ZAKEN_HEROPENEN
)
from zrc.api.tests.mixins import ZaakInformatieObjectSyncMixin
from zrc.datamodel.tests.factories import (
    ZaakEigenschapFactory, ZaakFactory, ZaakInformatieObjectFactory,
    ZaakObjectFactory
)

from .utils import ZAAK_WRITE_KWARGS, isodatetime

# ZTC
ZTC_ROOT = 'https://example.com/ztc/api/v1'
CATALOGUS = f'{ZTC_ROOT}/catalogus/878a3318-5950-4642-8715-189745f91b04'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
RESULTAATTYPE = f'{ZAAKTYPE}/resultaattypen/5b348dbf-9301-410b-be9e-83723e288785'
STATUSTYPE = f'{ZAAKTYPE}/statustypen/5b348dbf-9301-410b-be9e-83723e288785'

# DRC
DRC_ROOT = 'https://example.com/drc/api/v1'
ENKELVOUDIGINFORMATIEOBJECT = f'{DRC_ROOT}/enkelvoudiginformatieobjecten/8d4ad968-35b6-11e9-b210-d663bd873d93'

VERANTWOORDELIJKE_ORGANISATIE = '517439943'

BEGIN_STATUSTYPE_RESPONSE = {
    'url': STATUSTYPE,
    'zaaktype': ZAAKTYPE,
    'volgnummer': 1,
    'isEindstatus': False,
}

EIND_STATUSTYPE_RESPONSE = {
    'url': STATUSTYPE,
    'zaaktype': ZAAKTYPE,
    'volgnummer': 2,
    'isEindstatus': True,
}


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient',
)
class US345TestCase(ZaakInformatieObjectSyncMixin, JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_ALLES_LEZEN]
    # TODO: Required for PATCH to work! This should work without or otherwise, why can I create a ZAAK without this?
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_zaak_causes_archiving_defaults(self, *mocks):
        """
        Create ZAAK and validate default archive attributes
        """
        zaak_create_url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'startdatum': '2018-07-25',
            'einddatum': '2018-08-25',
            'einddatumGepland': '2018-08-25',
            'toelichting': '',
            'omschrijving': '',
        }

        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()

        self.assertIsNone(data['archiefnominatie'])
        self.assertEqual(data['archiefstatus'], Archiefstatus.nog_te_archiveren)
        self.assertIsNone(data['archiefactiedatum'])

    def test_can_set_archiefnominatie(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefnominatie': Archiefnominatie.vernietigen
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefactiedatum(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefactiedatum': date(2019, 1, 1)
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_without_archiefnominatie_and_archiefactiedatum(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_can_set_archiefstatus_with_archiefnominatie_and_archiefactiedatum(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefnominatie': Archiefnominatie.vernietigen,
            'archiefactiedatum': date(2019, 1, 1),
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefstatus_when_archiefnominatie_and_archiefactiedatum_already_set(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
            zaaktype=ZAAKTYPE
        )
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefstatus_when_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
            zaaktype=ZAAKTYPE
        )
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak,
            informatieobject=ENKELVOUDIGINFORMATIEOBJECT,
        )

        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        responses = {
            ENKELVOUDIGINFORMATIEOBJECT: {
                'url': ENKELVOUDIGINFORMATIEOBJECT,
                'status': 'gearchiveerd',
            },
        }

        with mock_client(responses):
            response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
            zaaktype=ZAAKTYPE
        )
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak,
            informatieobject=ENKELVOUDIGINFORMATIEOBJECT,
        )

        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        responses = {
            ENKELVOUDIGINFORMATIEOBJECT: {
                'url': ENKELVOUDIGINFORMATIEOBJECT,
                'status': 'in_bewerking',
            },
        }

        with mock_client(responses):
            response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_causes_archiefnominatie_to_be_copied(self, *mocks):
        """
        Add RESULTAAT that causes `archiefnominatie` to be copied from RESULTAATTYPE.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        # add a result for the case
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefnominatie)

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
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefnominatie, Archiefnominatie.blijvend_bewaren)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_without_einddatum(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain `None`.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
                    'datumkenmerk': None,
                    'objecttype': None,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: BEGIN_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_einddatum_causes_archiefactiedatum_to_be_set(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create(einddatum=date(2019, 1, 1), zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

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
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        self.autorisatie.scopes = self.autorisatie.scopes + [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_eigenschap_causes_archiefactiedatum_to_be_set(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        ZaakEigenschapFactory.create(
            zaak=zaak,
            _naam='brondatum',
            waarde=isodatetime(2019, 1, 1)
        )

        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.eigenschap,
                    'datumkenmerk': 'brondatum',
                    'objecttype': None,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_incorrect_eigenschap_fails(self, *mocks):
        """
        Attempt to add RESULTAAT with incorrect ZTC-configuration.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                # ZTC indicates there is a EIGENSCHAP called "brondatum", but there isn't one.
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.eigenschap,
                    'datumkenmerk': 'brondatum',
                    'objecttype': None,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_hoofdzaak_causes_archiefactiedatum_to_be_set(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        hoofd_zaak = ZaakFactory.create(einddatum=date(2019, 1, 1), zaaktype=ZAAKTYPE)

        zaak = ZaakFactory.create(hoofdzaak=hoofd_zaak, zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
                    'datumkenmerk': None,
                    'objecttype': None,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_ander_datumkenmerk_causes_archiefactiedatum_to_remain_empty(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain empty. It needs to be manually set based on the
        information in the RESULTAATTYPE.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
                    'datumkenmerk': 'einddatum',
                    'registratie': 'LichtgevendeObjectenRegistratie',
                    'objecttype': 'Lantaarnpaal',
                    'procestermijn': None,
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_zaakobject_causes_archiefactiedatum_to_be_set(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        zaak_object = ZaakObjectFactory.create(zaak=zaak)
        responses = {
            zaak_object.object: {
                'einddatum': isodatetime(2019, 1, 1)
            },
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P10Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.zaakobject,
                    'datumkenmerk': 'einddatum',
                    'objecttype': zaak_object.object_type,
                    'procestermijn': None,
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_add_resultaat_on_zaak_with_procestermijn_causes_archiefactiedatum_to_be_set(self, *mocks):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': RESULTAATTYPE,
            'toelichting': '',
        }

        responses = {
            RESULTAATTYPE: {
                'url': RESULTAATTYPE,
                'zaaktype': ZAAKTYPE,
                'archiefactietermijn': 'P5Y',
                'archiefnominatie': Archiefnominatie.blijvend_bewaren,
                'brondatumArchiefprocedure': {
                    'afleidingswijze': BrondatumArchiefprocedureAfleidingswijze.termijn,
                    'datumkenmerk': None,
                    'objecttype': None,
                    'procestermijn': 'P5Y',
                }
            },
            STATUSTYPE: EIND_STATUSTYPE_RESPONSE
        }

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': STATUSTYPE,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))
