# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)


@disable_admin_mfa()
class EnkelvoudigInformatieObjectCanonicalAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_delete_last_inline_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobjectcanonical_change",
            args=[canonical.pk],
        )

        response = self.app.get(url)
        form = response.forms["enkelvoudiginformatieobjectcanonical_form"]

        form["enkelvoudiginformatieobject_set-0-DELETE"] = True

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Een canonical moet minstens 1 versie hebben")

    def test_delete_second_to_last_inline_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()
        EnkelvoudigInformatieObjectFactory.create(canonical=canonical)

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobjectcanonical_change",
            args=[canonical.pk],
        )

        response = self.app.get(url)
        form = response.forms["enkelvoudiginformatieobjectcanonical_form"]

        form["enkelvoudiginformatieobject_set-0-DELETE"] = True

        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Een canonical moet minstens 1 versie hebben")
