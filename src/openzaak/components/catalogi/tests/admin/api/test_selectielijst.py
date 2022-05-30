# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from rest_framework import status
from rest_framework.reverse import reverse_lazy
from rest_framework.test import APITestCase

from openzaak.accounts.tests.factories import UserFactory
from openzaak.selectielijst.models import ReferentieLijstConfig

from ...factories import ZaakTypeFactory


class SelectieLijstResultatenTests(APITestCase):
    endpoint = reverse_lazy("admin-api:selectielijst-resultaten")

    def test_authentication_required(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_required(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaaktype_query_param(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user=user)

        with self.subTest("param missing"):
            response = self.client.get(self.endpoint)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid = ("", "aaa", 999)  # ID that doesn't exist
        for value in invalid:
            with self.subTest(value=value):
                response = self.client.get(self.endpoint, {"zaaktype": value})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zaaktype_without_procestype(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user=user)
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype="")

        response = self.client.get(self.endpoint, {"zaaktype": zaaktype.id})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0][0], "")

    def test_zaaktype_with_procestype(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user=user)
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype="https://example.com"
        )
        mock_choices = [
            ("https://example.com/1", "Example 1"),
            ("https://example.com/2", "Example 2"),
        ]

        with patch(
            "openzaak.components.catalogi.api.admin.views.get_selectielijst_resultaat_choices"
        ) as mock_get_choices:
            mock_get_choices.return_value = mock_choices
            response = self.client.get(self.endpoint, {"zaaktype": zaaktype.id})

        self.assertEqual(response.data, mock_choices)


class SelectieLijstProcestypenTests(APITestCase):
    endpoint = reverse_lazy("admin-api:selectielijst-procestypen")

    def setUp(self):
        super().setUp()

        patcher = patch(
            "openzaak.components.catalogi.api.admin.views.ReferentieLijstConfig.get_solo",
            return_value=ReferentieLijstConfig(allowed_years=[2017, 2020]),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_authentication_required(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_required(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_year_query_param(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user=user)

        with self.subTest("param missing"):
            response = self.client.get(self.endpoint)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid = ("", "aaa", 2015)
        for value in invalid:
            with self.subTest(value=value):
                response = self.client.get(self.endpoint, {"year": value})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_year(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user=user)
        mock_choices = [
            {"url": "https://example.com/1", "naam": "Example 1"},
            {"url": "https://example.com/2", "naam": "Example 2"},
        ]

        with patch(
            "openzaak.components.catalogi.api.admin.views.get_procestypen"
        ) as mock_get_choices:
            mock_get_choices.return_value = mock_choices
            response = self.client.get(self.endpoint, {"year": 2017})

        mock_get_choices.assert_called_once_with(procestype_jaar=2017)

        self.assertEqual(response.data, mock_choices)
