# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact

from rest_framework.test import APITestCase
from vng_api_common.client import get_client
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils.cache import DjangoRequestsCache, requests_cache_enabled


class DjangoRequestsCacheTests(APITestCase):
    def test_backend(self):
        # Example of an endpoint where the requests_cache_enabled decorator is used
        ServiceFactory.create(api_root="https://example.com/procestypen/")
        zaak_type = ZaakTypeFactory.create(
            selectielijst_procestype="https://example.com/procestypen/1234",
        )
        with requests_cache_enabled():
            self.client = get_client(
                zaak_type.selectielijst_procestype,
                raise_exceptions=True,
            )
            backend = getattr(self.client, "cache", None)
            assert isinstance(backend, DjangoRequestsCache)
