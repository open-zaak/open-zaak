# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.tests.utils import JWTAuthMixin

from .factories import ResultaatFactory
from .utils import get_operation_url


@override_settings(ALLOWED_HOSTS=["testserver"])
class ResultaatListTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("resultaat_create")

    def test_pagination_pagesize_param(self):
        ResultaatFactory.create_batch(10)

        response = self.client.get(self.list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )
