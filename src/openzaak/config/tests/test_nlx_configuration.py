# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from django_webtest import WebTest

from openzaak.utils.tests import AdminTestMixin


class NLXConfigTests(AdminTestMixin, WebTest):
    url = reverse_lazy("config:config-nlx")

    def test_outway_invalid_address(self):
        config_page = self.app.get(self.url, user=self.user)
        form = config_page.form

        form["outway"] = "invalid-host.local:1337"
        response = form.submit()

        # form validation errors -> no redirect
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            "form",
            "__all__",
            _("Connection refused. Please provide a correct address."),
        )
