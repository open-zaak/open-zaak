# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import override_settings, tag

from maykin_2fa.test import disable_admin_mfa
from playwright.sync_api import expect

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.autorisaties.tests.factories import ApplicatieFactory
from openzaak.tests.utils.playwright import PlaywrightSyncLiveServerTestCase


@tag("playwright")
@override_settings(AXES_ENABLED=False)
@disable_admin_mfa()
class AutorisatiesAdminFormTests(PlaywrightSyncLiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.user = SuperUserFactory.create()
        self.login_state = self.get_user_login_state(self.user)

    def test_autorisaties_form_renders_correctly(self):
        context = self.browser.new_context(storage_state=self.login_state)

        page = context.new_page()

        applicatie = ApplicatieFactory.create()

        page.goto(
            self.live_reverse(
                "admin:authorizations_applicatie_autorisaties",
                kwargs={"object_id": applicatie.pk},
            )
        )

        expect(page.get_by_text("Nog Autorisaties toevoegen")).to_be_visible()

        page.get_by_label("Zaken API").check()

        # Form should be changed due to selected API
        expect(page.get_by_text("Selecteer handmatig")).to_be_visible()
        expect(page.get_by_text("Selecteer catalogus")).to_be_visible()
        expect(
            page.get_by_text("Tot en met welke vertrouwelijkheidaanduiding")
        ).to_be_visible()
