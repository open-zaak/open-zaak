"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/345
"""
from datetime import date
from openzaak.components.zaken.api.tests.utils import get_operation_url
from openzaak.components.zaken.models.tests.factories import (
    ZaakEigenschapFactory, ZaakFactory, ZaakInformatieObjectFactory,
    ZaakObjectFactory
)
from openzaak.components.catalogi.models.tests.factories import ZaakTypeFactory, ResultaatTypeFactory, StatusTypeFactory
from openzaak.components.documenten.models.tests.factories import EnkelvoudigInformatieObjectFactory
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie, Archiefstatus, BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding
)
from vng_api_common.tests import JWTAuthMixin, reverse
from zds_client.tests.mocks import mock_client

from .utils import ZAAK_WRITE_KWARGS, isodatetime

VERANTWOORDELIJKE_ORGANISATIE = '517439943'


class US345TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_create_zaak_causes_archiving_defaults(self):
        """
        Create ZAAK and validate default archive attributes
        """
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        zaak_create_url = get_operation_url('zaak_create')
        data = {
            'zaaktype': f'http://testserver{zaaktype_url}',
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
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefnominatie': Archiefnominatie.vernietigen
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefactiedatum(self):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefactiedatum': date(2019, 1, 1)
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_without_archiefnominatie_and_archiefactiedatum(self):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)

        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_can_set_archiefstatus_with_archiefnominatie_and_archiefactiedatum(self):
        zaak = ZaakFactory.create()
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
        )
        io = EnkelvoudigInformatieObjectFactory.create(status='gearchiveerd')
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak,
            informatieobject=io.canonical,
        )
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)
        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status='in_bewerking')
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak,
            informatieobject=io.canonical,
        )
        zaak_patch_url = get_operation_url('zaak_partial_update', uuid=zaak.uuid)
        data = {
            'archiefstatus': Archiefstatus.gearchiveerd
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_add_resultaat_on_zaak_causes_archiefnominatie_to_be_copied(self):
        """
        Add RESULTAAT that causes `archiefnominatie` to be copied from RESULTAATTYPE.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)

        # add a result for the case
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }
        self.assertIsNone(zaak.archiefnominatie)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefnominatie, Archiefnominatie.blijvend_bewaren)

    def test_add_resultaat_on_zaak_without_einddatum(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain `None`.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_add_resultaat_on_zaak_with_einddatum_causes_archiefactiedatum_to_be_set(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create(einddatum=date(2019, 1, 1))
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')

        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))

    def test_add_resultaat_on_zaak_with_eigenschap_causes_archiefactiedatum_to_be_set(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        ZaakEigenschapFactory.create(
            zaak=zaak,
            _naam='brondatum',
            waarde=isodatetime(2019, 1, 1)
        )
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            brondatum_archiefprocedure_datumkenmerk='brondatum',
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_add_resultaat_on_zaak_with_incorrect_eigenschap_fails(self):
        """
        Attempt to add RESULTAAT with incorrect ZTC-configuration.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            brondatum_archiefprocedure_datumkenmerk='brondatum',
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_resultaat_on_zaak_with_hoofdzaak_causes_archiefactiedatum_to_be_set(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        hoofd_zaak = ZaakFactory.create(einddatum=date(2019, 1, 1))

        zaak = ZaakFactory.create(hoofdzaak=hoofd_zaak)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url('status_create')
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_add_resultaat_on_zaak_with_ander_datumkenmerk_causes_archiefactiedatum_to_remain_empty(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain empty. It needs to be manually set based on the
        information in the RESULTAATTYPE.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
            brondatum_archiefprocedure_datumkenmerk='einddatum',
            brondatum_archiefprocedure_registratie='LichtgevendeObjectenRegistratie',
            brondatum_archiefprocedure_objecttype='Lantaarnpaal',
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_add_resultaat_on_zaak_with_zaakobject_causes_archiefactiedatum_to_be_set(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        zaak_object = ZaakObjectFactory.create(zaak=zaak)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P10Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.zaakobject,
            brondatum_archiefprocedure_datumkenmerk='einddatum',
            brondatum_archiefprocedure_objecttype=zaak_object.object_type,
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        responses = {
            zaak_object.object: {
                'einddatum': isodatetime(2019, 1, 1)
            },
        }

        # add resultaat
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_add_resultaat_on_zaak_with_procestermijn_causes_archiefactiedatum_to_be_set(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn='P5Y',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.termijn,
            brondatum_archiefprocedure_procestermijn='P5Y',
            zaaktype=zaak.zaaktype
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url('resultaat_create')
        data = {
            'zaak': zaak_url,
            'resultaattype': resultaattype_url,
            'toelichting': '',
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url('status_create')
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            'zaak': zaak_url,
            'statustype': statustype_url,
            'datumStatusGezet': '2018-10-18T20:00:00Z',
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))
