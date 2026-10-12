# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import TestCase
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.models import Zaak, ZaakBesluit
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import AdminTestMixin

from ...models import Besluit, BesluitInformatieObject
from ..factories import BesluitFactory, BesluitInformatieObjectFactory


@disable_admin_mfa()
class BesluitAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_non_alphanumeric_identificatie_validation(self):
        """
        Edit a zaak with an identificatie allowed by the API.

        This should not trigger validation errors.
        """
        besluit = BesluitFactory.create(identificatie="ZK bläh")
        url = reverse("admin:besluiten_besluit_change", args=(besluit.pk,))
        response = self.app.get(url)
        form = response.forms["besluit_form"]

        self.assertEqual(form["identificatie"].value, "ZK bläh")
        submit_response = form.submit()

        self.assertEqual(submit_response.status_code, 302)


@disable_admin_mfa()
class BesluitAdminDeleteTests(AdminTestMixin, TestCase):
    def _create_besluit(self) -> Besluit:
        besluit = BesluitFactory.create(zaak=ZaakFactory.create())
        BesluitInformatieObjectFactory.create(besluit=besluit)
        return besluit

    def test_delete_besluit_with_zaak_and_informatieobject(self):
        besluit = self._create_besluit()
        delete_url = reverse("admin:besluiten_besluit_delete", args=(besluit.pk,))

        response = self.client.post(delete_url, {"post": "yes"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertFalse(ZaakBesluit.objects.exists())
        self.assertTrue(Zaak.objects.exists())

    def test_delete_selected_besluiten_with_zaak_and_informatieobject(self):
        besluit = self._create_besluit()
        change_list_url = reverse("admin:besluiten_besluit_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [besluit.pk],
            "post": "yes",
        }

        response = self.client.post(change_list_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertFalse(ZaakBesluit.objects.exists())
