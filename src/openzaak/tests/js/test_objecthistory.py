# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.test import override_settings, tag
from django.utils.translation import gettext as _

from maykin_2fa.test import disable_admin_mfa
from playwright.sync_api import expect

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils.playwright import PlaywrightSyncLiveServerTestCase


@tag("playwright")
@override_settings(AXES_ENABLED=False)
@disable_admin_mfa()
class ObjectHistoryTests(PlaywrightSyncLiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.user = SuperUserFactory.create()
        self.login_state = self.get_user_login_state(self.user)

    def test_object_history_page_without_trails(self):
        zaak = ZaakFactory.create()

        context = self.browser.new_context(storage_state=self.login_state)

        page = context.new_page()

        page.goto(self.live_reverse("admin:zaken_zaak_history", args=(zaak.pk,)))

        page.wait_for_url(
            self.live_reverse("admin:zaken_zaak_history", args=(zaak.pk,))
        )

        expect(
            page.get_by_text(
                _(
                    "This object doesn’t have a change history. It probably wasn’t added via this admin site."
                )
            )
        ).to_be_visible()

    def test_object_history_page_with_trails(self):
        zaak = ZaakFactory.create()
        context = self.browser.new_context(storage_state=self.login_state)
        page = context.new_page()
        page.goto(self.live_reverse("admin:zaken_zaak_change", args=(zaak.pk,)))

        # create 5 audittrails
        for i in range(5):
            page.fill("#id_toelichting", f"test {i}")
            page.get_by_role("button", name=_("Save and continue editing")).click()
            page.wait_for_url(
                self.live_reverse("admin:zaken_zaak_change", args=(zaak.pk,))
            )

        page.goto(self.live_reverse("admin:zaken_zaak_history", args=(zaak.pk,)))

        # 5 audittrail rows are shown
        buttons = page.locator(f"text={_('Toon wijzigingen')}")
        self.assertEqual(buttons.count(), 5)

        # on page load no changed fields are shown
        expect(page.get_by_text(_("Gewijzigde velden"))).to_be_hidden()

        # toon wijzigingen
        buttons.first.click()
        expect(page.get_by_text("Gewijzigde velden")).to_be_visible()

        # expect table text
        table_div = page.locator("#detail-1 table")
        expect(table_div).to_be_visible()
        text = [t.strip() for t in table_div.text_content().split() if t.strip()]
        self.assertEqual(
            text,
            [
                _("veld"),
                _("oud"),
                _("nieuw"),
                "toelichting",
                "test",
                "3",
                "test",
                "4",
            ],
        )

        # expect other tables to be hidden
        expect(page.get_by_text("#detail-2")).to_be_hidden()
        expect(page.get_by_text("#detail-3")).to_be_hidden()
        expect(page.get_by_text("#detail-4")).to_be_hidden()
        expect(page.get_by_text("#detail-5")).to_be_hidden()

        # expect 1 button to be disabled
        disabled_buttons = page.locator("button.audit-button:disabled")
        self.assertEqual(disabled_buttons.count(), 1)

        # select different one
        buttons.nth(1).click()
        expect(page.get_by_text("Gewijzigde velden")).to_be_visible()

        # expect table text
        table_div = page.locator("#detail-2 table")
        expect(table_div).to_be_visible()
        text = [t.strip() for t in table_div.text_content().split() if t.strip()]
        self.assertEqual(
            text, ["veld", "oud", "nieuw", "toelichting", "test", "2", "test", "3"]
        )

        # expect other tables to be hidden
        expect(page.get_by_text("#detail-1")).to_be_hidden()
        expect(page.get_by_text("#detail-3")).to_be_hidden()
        expect(page.get_by_text("#detail-4")).to_be_hidden()
        expect(page.get_by_text("#detail-5")).to_be_hidden()

        # expect 1 button to be disabled
        disabled_buttons = page.locator("button.audit-button:disabled")
        self.assertEqual(disabled_buttons.count(), 1)
