# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..models import BesluitInformatieObject
from .factories import BesluitInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class BesluitInformatieObjectCMISAPIFilterTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_validate_unknown_query_params(self):
        for counter in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()
            BesluitInformatieObjectFactory.create(informatieobject=eio_url)
        url = reverse(BesluitInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        BesluitInformatieObjectFactory.create(informatieobject=eio_url)
        response = self.client.get(
            reverse(BesluitInformatieObject), {"besluit": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
