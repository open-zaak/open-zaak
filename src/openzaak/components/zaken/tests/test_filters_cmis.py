# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..models import ZaakInformatieObject
from .factories import ZaakInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectFilterCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()

        self.zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])
