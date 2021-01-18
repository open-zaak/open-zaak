# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.constants import ComponentTypes

from openzaak.utils.constants import COMPONENT_MAPPING
from openzaak.utils.tests import AdminTestMixin

from ..models import InternalService
from .factories import InternalServiceFactory


class InternalServicesFormTests(AdminTestMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        for api_type in COMPONENT_MAPPING.values():
            InternalServiceFactory.create(api_type=api_type)

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_autorisaties_enabled(self):
        autorisaties = InternalService.objects.get(api_type=ComponentTypes.ac)
        assert autorisaties.enabled is True

        add_url = reverse("config:config-internal")

        get_response = self.app.get(add_url)

        form = get_response.form
        # make sure that autorisaties service is in form-0 of formset
        assert int(form["form-0-id"].value) == autorisaties.id

        # disable another service
        other_service = InternalService.objects.get(id=int(form["form-1-id"].value))
        form["form-1-enabled"].checked = False

        form.submit()

        autorisaties.refresh_from_db()
        other_service.refresh_from_db()

        self.assertEqual(autorisaties.enabled, True)
        self.assertEqual(other_service.enabled, False)
