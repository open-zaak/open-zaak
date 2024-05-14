# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import StatusType
from ..factories import ZaakTypeFactory


@tag("gh-1042")
@disable_admin_mfa()
class StatusTypeAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_create_statustype_for_published_zaaktype_not_allowed(self):
        zaaktype = ZaakTypeFactory.create(concept=False)

        response = self.app.get(reverse("admin:catalogi_statustype_add"))

        response.form["statustype_omschrijving"] = "foo"
        response.form["statustypevolgnummer"] = 1
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
        self.assertEqual(StatusType.objects.count(), 0)
