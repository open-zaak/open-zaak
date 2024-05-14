# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.constants import RolOmschrijving

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import RolType
from ..factories import RolTypeFactory, ZaakTypeFactory


@tag("gh-1042")
@disable_admin_mfa()
class RolTypeAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_create_roltype_for_published_zaaktype_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.app.get(reverse("admin:catalogi_roltype_add"))

        response.form["omschrijving"] = "foo"
        response.form["omschrijving_generiek"] = RolOmschrijving.adviseur
        response.form["zaaktype"] = zaaktype.id
        response = response.form.submit()

        self.assertEqual(
            response.context["adminform"].errors,
            {
                "zaaktype": [
                    _(
                        "Creating a relation to non-concept {resource} is forbidden"
                    ).format(resource="zaaktype")
                ]
            },
        )
        self.assertEqual(RolType.objects.count(), 0)

    def test_update_roltype_published_zaaktype_fail_validation(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create()

        response = self.app.get(
            reverse("admin:catalogi_roltype_change", args=(roltype.pk,))
        )

        response.form["omschrijving"] = "foo"
        response.form["omschrijving_generiek"] = RolOmschrijving.adviseur
        response.form["zaaktype"] = zaaktype.id
        response = response.form.submit()

        self.assertEqual(
            response.context["adminform"].errors,
            {
                "zaaktype": [
                    _(
                        "Creating a relation to non-concept {resource} is forbidden"
                    ).format(resource="zaaktype")
                ]
            },
        )
        self.assertIn("zaaktype", response.form.fields)

        roltype.refresh_from_db()

        self.assertNotEqual(roltype.zaaktype, zaaktype)
