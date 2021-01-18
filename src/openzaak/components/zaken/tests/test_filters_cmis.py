# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..models import ZaakInformatieObject
from .factories import ZaakInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectFilterCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    heeft_alle_autorisaties = True

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        self.create_zaak_besluit_services()
        self.zio = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url, zaak=self.create_zaak()
        )
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])
