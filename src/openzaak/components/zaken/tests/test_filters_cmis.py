from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ...documenten.tests.utils import serialise_eio
from ..models import ZaakInformatieObject
from .factories import ZaakInformatieObjectFactory


@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectFilterCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "bla"}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.register_uri("GET", eio_url, json=serialise_eio(eio, eio_url))
        self.zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])
