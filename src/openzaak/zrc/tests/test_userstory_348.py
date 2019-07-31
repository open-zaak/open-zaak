"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/348
"""
from datetime import date
from urllib.parse import quote_plus, urlencode

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import Archiefnominatie, Archiefstatus
from vng_api_common.tests import JWTAuthMixin, get_operation_url

from zrc.api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
from zrc.datamodel.tests.factories import ZaakFactory

from .utils import ZAAK_WRITE_KWARGS

ZAAKTYPE = 'https://example.com/api/v1/zaaktype/1'


class US345TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    # TODO: Required for PATCH to work! This should work without or otherwise, why can I create a ZAAK without this?
    zaaktype = ZAAKTYPE

    def test_filter_on_archiefactiedatum_archiefnominatie_archiefstatus(self):
        zaak_1 = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            archiefactiedatum=date(2010, 1, 1),
            archiefstatus=Archiefstatus.nog_te_archiveren,
            zaaktype=ZAAKTYPE
        )
        zaak_2 = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date(2010, 1, 1),
            archiefstatus=Archiefstatus.nog_te_archiveren,
            zaaktype=ZAAKTYPE
        )

        zaak_list_url = get_operation_url('zaak_list')

        query_params = {
            'archiefactiedatum__lt': date(2015, 1, 1),
            'archiefnominatie': Archiefnominatie.blijvend_bewaren,
            'archiefstatus__in': ','.join([Archiefstatus.nog_te_archiveren, Archiefstatus.gearchiveerd]),
        }
        query_params = urlencode(query_params, quote_via=quote_plus)

        response = self.client.get(f'{zaak_list_url}?{query_params}', **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()['results']
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]['url'].endswith(str(zaak_1.uuid)))
