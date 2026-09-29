# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import TestCase
from django.urls import reverse

from maykin_2fa.test import disable_admin_mfa

from openzaak.tests.utils.admin import AdminTestMixin

from ..factories import VerzendingFactory


@disable_admin_mfa()
class VerzendingAdminTests(AdminTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.verzending = VerzendingFactory.create()
        cls.verzending_same_io = VerzendingFactory.create(
            informatieobject=cls.verzending.informatieobject,
            contactpersoonnaam="Verzending contactpersoonnaam",
        )
        VerzendingFactory.create_batch(10)
        cls.url = reverse("admin:documenten_verzending_changelist")

    def test_search_no_result(self):
        response = self.client.get(self.url, {"q": "no-result-in-query"})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["cl"].result_list, [])

    def test_search_by_contactpersoonnaam(self):
        response = self.client.get(
            self.url, {"q": self.verzending_same_io.contactpersoonnaam}
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["cl"].result_list, [self.verzending_same_io]
        )

    def test_search_by_uuid(self):
        response = self.client.get(self.url, {"q": self.verzending.uuid})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["cl"].result_list, [self.verzending])

    def test_search_by_informatieobject(self):
        io = self.verzending.informatieobject.latest_version

        # Search by informatieobject uuid or identificatie
        for search_text in (str(io.uuid), io.identificatie):
            with self.subTest(search_text=search_text):
                response = self.client.get(self.url, {"q": search_text})
                self.assertEqual(response.status_code, 200)
                self.assertQuerySetEqual(
                    response.context["cl"].result_list,
                    [self.verzending_same_io, self.verzending],
                )
