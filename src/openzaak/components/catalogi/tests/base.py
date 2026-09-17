# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.test import APITestCase as _APITestCase

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import Catalogus
from .factories import CatalogusFactory


class CatalogusAPITestMixin:
    API_VERSION = "1"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # type: ignore

        cls.catalogus = CatalogusFactory.create(domein="ABCDE", rsin="000000001")

        cls.catalogus_list_url = reverse(Catalogus)
        cls.catalogus_detail_url = reverse(cls.catalogus)


class APITestCase(CatalogusAPITestMixin, JWTAuthMixin, _APITestCase):
    heeft_alle_autorisaties = True
