# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
)
from openzaak.selectielijst.tests import (
    mock_selectielijst_oas_get,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.tests.utils import ClearCachesMixin
from openzaak.tests.utils.admin import AdminTestMixin


@disable_admin_mfa()
@requests_mock.Mocker()
class ReadonlyAdminTests(
    ReferentieLijstServiceMixin, ClearCachesMixin, AdminTestMixin, WebTest
):
    def test_readonly_besluittype(self, m):
        """
        check that in case of published besluittype only "datum_einde_geldigheid" field is editable
        """
        mock_selectielijst_oas_get(m)

        besluittype = BesluitTypeFactory.create(concept=False)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        response = self.app.get(url)

        form = response.forms["besluittype_form"]
        form_fields = list(form.fields.keys())
        besluittype_fields = [
            f.name
            for f in besluittype._meta.get_fields()
            if f.name != "datum_einde_geldigheid"
        ]

        self.assertEqual("datum_einde_geldigheid" in form_fields, True)
        for field in besluittype_fields:
            self.assertEqual(field in form_fields, False)
