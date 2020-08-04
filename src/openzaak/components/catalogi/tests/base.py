# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.test import APITestCase as _APITestCase

from openzaak.utils.tests import JWTAuthMixin

from .factories import CatalogusFactory
from .utils import get_operation_url


class CatalogusAPITestMixin:
    API_VERSION = "1"

    def setUp(self):
        super().setUp()

        self.catalogus = CatalogusFactory.create(domein="ABCDE", rsin="000000001")

        self.catalogus_list_url = get_operation_url("catalogus_list")
        self.catalogus_detail_url = get_operation_url(
            "catalogus_read", uuid=self.catalogus.uuid
        )


class APITestCase(CatalogusAPITestMixin, JWTAuthMixin, _APITestCase):
    heeft_alle_autorisaties = True
