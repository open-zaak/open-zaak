# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from django.urls import reverse

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
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
    def test_readonly_informatieobjecttype(self, m):
        """
        check that in case of published informatieobjecttype only "datum_einde_geldigheid" field is editable
        """
        mock_selectielijst_oas_get(m)

        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)

        form = response.forms["informatieobjecttype_form"]
        form_fields = list(form.fields.keys())
        informatieobjecttype_fields = [
            f.name
            for f in informatieobjecttype._meta.get_fields()
            if f.name != "datum_einde_geldigheid"
        ]

        self.assertEqual("datum_einde_geldigheid" in form_fields, True)
        for field in informatieobjecttype_fields:
            self.assertEqual(field in form_fields, False)
