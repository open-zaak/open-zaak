# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import override_settings, tag
from django.utils.translation import gettext as _

from maykin_2fa.test import disable_admin_mfa
from playwright.sync_api import expect
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.autorisaties.api.scopes import SCOPE_AUTORISATIES_LEZEN
from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    AutorisatieFactory,
)
from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_ALLES_LEZEN,
    SCOPE_BESLUITEN_BIJWERKEN,
)
from openzaak.components.catalogi.api.scopes import (
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from openzaak.components.catalogi.tests.factories import CatalogusFactory
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
)
from openzaak.notifications.scopes import SCOPE_CLOUDEVENTS_BEZORGEN
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

    @tag("gh-2647")
    def test_add_multiple_different_component_with_different_scopes_in_autorisaties_form(
        self,
    ):
        """
        Create six rows for the different component with different scopes in one submission
        - Autorisaties API (SCOPE_AUTORISATIES_LEZEN)
        - Notificaties API (SCOPE_CLOUDEVENTS_BEZORGEN)
        - Zaken API (SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_ALLES_VERWIJDEREN)
        - Catalogi API (SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE)
        - Documenten API (SCOPE_DOCUMENTEN_ALLES_LEZEN, SCOPE_DOCUMENTEN_BIJWERKEN)
        - Besluiten API (SCOPE_BESLUITEN_ALLES_LEZEN, SCOPE_BESLUITEN_BIJWERKEN)
        """

        context = self.browser.new_context(storage_state=self.login_state)
        self.addCleanup(context.close)
        page = context.new_page()
        applicatie = ApplicatieFactory.create()
        catalogus = CatalogusFactory.create()

        authorization_url = self.live_reverse(
            "admin:authorizations_applicatie_autorisaties", args=(applicatie.pk,)
        )
        page.goto(authorization_url)

        forms = page.locator(".autorisatie-form")
        total_forms = page.locator('input[name="form-TOTAL_FORMS"]')
        add_link = page.get_by_role("link", name="Nog Autorisaties toevoegen")

        rows = [
            ("Autorisaties API", [SCOPE_AUTORISATIES_LEZEN]),
            ("Notificaties API", [SCOPE_CLOUDEVENTS_BEZORGEN]),
            ("Zaken API", [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_ALLES_VERWIJDEREN]),
            ("Catalogi API", [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]),
            (
                "Documenten API",
                [SCOPE_DOCUMENTEN_ALLES_LEZEN, SCOPE_DOCUMENTEN_BIJWERKEN],
            ),
            (
                "Besluiten API",
                [SCOPE_BESLUITEN_ALLES_LEZEN, SCOPE_BESLUITEN_BIJWERKEN],
            ),
        ]
        # Components that require extra parameters
        needs_catalogus = {"Zaken API", "Documenten API", "Besluiten API"}
        # Components that also require a vertrouwelijkheidaanduiding
        needs_vertrouwelijkheidaanduiding = {"Zaken API", "Documenten API"}

        for index, (component, scopes) in enumerate(rows):
            if index > 0:
                add_link.click()
            expect(forms).to_have_count(index + 1)
            expect(total_forms).to_have_value(str(index + 1))

            form = forms.nth(index)
            form.get_by_label(component, exact=True).check()

            for scope in scopes:
                form.locator(f'input[value="{scope}"]').check()

            if component in needs_catalogus:
                form.locator('input[value="select_catalogus"]').check()
                form.locator(
                    f'input[name$="-catalogi"][value="{catalogus.pk}"]'
                ).check()

            if component in needs_vertrouwelijkheidaanduiding:
                form.locator(
                    f'input[value="{VertrouwelijkheidsAanduiding.openbaar}"]'
                ).check()

        # Earlier rows keep their selection after adding new rows
        for index, (component, scopes) in enumerate(rows):
            form = forms.nth(index)
            expect(form.get_by_label(component, exact=True)).to_be_checked()
            for scope in scopes:
                expect(form.locator(f'input[value="{scope}"]')).to_be_checked()

        with page.expect_response(
            lambda response: response.url == authorization_url
            and response.request.method == "POST"
        ) as save_response:
            page.locator('input[name="_save"]').click()
        self.assertEqual(save_response.value.status, 302)
        expect(page).to_have_url(
            self.live_reverse(
                "admin:authorizations_applicatie_change", args=(applicatie.pk,)
            )
        )

        # Check the success message
        expect(page.locator(".messagelist li.success")).to_have_text(
            f"De autorisaties voor applicatie ‘{applicatie}’ zijn met succes gewijzigd."
        )

        # Components without extra parameters are stored as Autorisatie
        self.assertCountEqual(
            applicatie.autorisaties.values_list("component", "scopes"),
            [
                (ComponentTypes.ac, [str(SCOPE_AUTORISATIES_LEZEN)]),
                (ComponentTypes.nrc, [str(SCOPE_CLOUDEVENTS_BEZORGEN)]),
                (
                    ComponentTypes.ztc,
                    [str(SCOPE_CATALOGI_READ), str(SCOPE_CATALOGI_WRITE)],
                ),
            ],
        )

        # Components with a catalogus selection are stored as CatalogusAutorisatie
        self.assertCountEqual(
            CatalogusAutorisatie.objects.filter(applicatie=applicatie).values_list(
                "component", "scopes", "catalogus"
            ),
            [
                (
                    ComponentTypes.zrc,
                    [str(SCOPE_ZAKEN_ALLES_LEZEN), str(SCOPE_ZAKEN_ALLES_VERWIJDEREN)],
                    catalogus.pk,
                ),
                (
                    ComponentTypes.drc,
                    [
                        str(SCOPE_DOCUMENTEN_BIJWERKEN),
                        str(SCOPE_DOCUMENTEN_ALLES_LEZEN),
                    ],
                    catalogus.pk,
                ),
                (
                    ComponentTypes.brc,
                    [str(SCOPE_BESLUITEN_BIJWERKEN), str(SCOPE_BESLUITEN_ALLES_LEZEN)],
                    catalogus.pk,
                ),
            ],
        )
        self.assertEqual(page.page_errors(), [])

    @tag("gh-2647")
    def test_add_multiple_same_component_with_different_scopes_in_autorisaties_form(
        self,
    ):
        # Save two rows with the same component with different scopes in one submission
        context = self.browser.new_context(storage_state=self.login_state)
        self.addCleanup(context.close)
        page = context.new_page()
        applicatie = ApplicatieFactory.create()

        authorization_url = self.live_reverse(
            "admin:authorizations_applicatie_autorisaties", args=(applicatie.pk,)
        )
        page.goto(authorization_url)

        forms = page.locator(".autorisatie-form")

        # Catalogi API with SCOPE_CATALOGI_READ
        forms.first.get_by_label("Catalogi API", exact=True).check()
        catalogi_scope = forms.first.locator(f'input[value="{SCOPE_CATALOGI_READ}"]')
        catalogi_scope.check()

        page.get_by_role("link", name="Nog Autorisaties toevoegen").click()
        expect(forms).to_have_count(2)

        forms.nth(1).get_by_label("Catalogi API", exact=True).check()
        # Catalogi API with SCOPE_CATALOGI_WRITE
        forms.nth(1).locator(f'input[value="{SCOPE_CATALOGI_WRITE}"]').check()

        expect(page.locator('input[name="form-TOTAL_FORMS"]')).to_have_value("2")
        expect(catalogi_scope).to_be_checked()

        with page.expect_response(
            lambda response: response.url == authorization_url
            and response.request.method == "POST"
        ) as save_response:
            page.locator('input[name="_save"]').click()

        self.assertEqual(save_response.value.status, 302)
        expect(page).to_have_url(
            self.live_reverse(
                "admin:authorizations_applicatie_change", args=(applicatie.pk,)
            )
        )

        # Check the success message
        expect(page.locator(".messagelist li.success")).to_have_text(
            f"De autorisaties voor applicatie ‘{applicatie}’ zijn met succes gewijzigd."
        )

        self.assertCountEqual(
            applicatie.autorisaties.values_list("component", "scopes"),
            [
                (ComponentTypes.ztc, [str(SCOPE_CATALOGI_READ)]),
                (ComponentTypes.ztc, [str(SCOPE_CATALOGI_WRITE)]),
            ],
        )
        self.assertEqual(page.page_errors(), [])

    @tag("gh-2647")
    def test_same_component_with_overlapping_scopes_shows_error(self):
        # Two rows with the same component and the same scope may not be saved
        context = self.browser.new_context(storage_state=self.login_state)
        self.addCleanup(context.close)
        page = context.new_page()
        applicatie = ApplicatieFactory.create()

        authorization_url = self.live_reverse(
            "admin:authorizations_applicatie_autorisaties", args=(applicatie.pk,)
        )
        page.goto(authorization_url)

        forms = page.locator(".autorisatie-form")

        forms.first.get_by_label("Catalogi API", exact=True).check()
        forms.first.locator(f'input[value="{SCOPE_CATALOGI_READ}"]').check()

        page.get_by_role("link", name="Nog Autorisaties toevoegen").click()
        expect(forms).to_have_count(2)

        forms.nth(1).get_by_label("Catalogi API", exact=True).check()
        forms.nth(1).locator(f'input[value="{SCOPE_CATALOGI_READ}"]').check()

        with page.expect_response(
            lambda response: response.url == authorization_url
            and response.request.method == "POST"
        ) as save_response:
            page.locator('input[name="_save"]').click()

        # Form is re-rendered with errors instead of redirecting
        self.assertEqual(save_response.value.status, 200)
        expect(page).to_have_url(authorization_url)
        expect(page.locator(".errornote")).to_be_visible()
        expect(page.locator(".errorlist").first).to_contain_text(
            _("Scopes in {component} may not be duplicated.").format(
                component=ComponentTypes.ztc
            )
        )
        expect(page.locator(".messagelist li.success")).to_have_count(0)

        self.assertFalse(applicatie.autorisaties.exists())
        self.assertEqual(page.page_errors(), [])

    @tag("gh-2647")
    def test_component_with_missing_extra_parameters_shows_error(self):
        # Zaken API requires a catalogus selection and a vertrouwelijkheidaanduiding
        context = self.browser.new_context(storage_state=self.login_state)
        self.addCleanup(context.close)
        page = context.new_page()
        applicatie = ApplicatieFactory.create()
        CatalogusFactory.create()

        authorization_url = self.live_reverse(
            "admin:authorizations_applicatie_autorisaties", args=(applicatie.pk,)
        )
        page.goto(authorization_url)

        form = page.locator(".autorisatie-form").first
        form.get_by_label("Zaken API", exact=True).check()
        form.locator(f'input[value="{SCOPE_ZAKEN_ALLES_LEZEN}"]').check()

        with page.expect_response(
            lambda response: response.url == authorization_url
            and response.request.method == "POST"
        ) as save_response:
            page.locator('input[name="_save"]').click()

        self.assertEqual(save_response.value.status, 200)
        expect(page).to_have_url(authorization_url)
        expect(page.locator(".errornote")).to_be_visible()

        # The errors are shown inside the component form
        form = page.locator(".autorisatie-form").first
        expect(form.get_by_label("Zaken API", exact=True)).to_be_checked()
        expect(
            form.locator(".errorlist").filter(
                has_text=_("Je moet een keuze opgeven voor het veld: {field}").split(
                    "{"
                )[0]
            )
        ).not_to_have_count(0)
        expect(page.locator(".messagelist li.success")).to_have_count(0)

        self.assertFalse(applicatie.autorisaties.exists())
        self.assertFalse(
            CatalogusAutorisatie.objects.filter(applicatie=applicatie).exists()
        )
        self.assertEqual(page.page_errors(), [])

    @tag("gh-2647")
    def test_save_with_existing_data_without_changes_shows_no_message_or_error(self):
        context = self.browser.new_context(storage_state=self.login_state)
        self.addCleanup(context.close)
        page = context.new_page()
        applicatie = ApplicatieFactory.create()
        AutorisatieFactory.create(
            applicatie=applicatie,
            component=ComponentTypes.ztc,
            scopes=[str(SCOPE_CATALOGI_READ)],
        )

        authorization_url = self.live_reverse(
            "admin:authorizations_applicatie_autorisaties", args=(applicatie.pk,)
        )
        page.goto(authorization_url)

        # Existing autorisatie is pre-filled
        form = page.locator(".autorisatie-form").first
        expect(form.get_by_label("Catalogi API", exact=True)).to_be_checked()
        expect(form.locator(f'input[value="{SCOPE_CATALOGI_READ}"]')).to_be_checked()

        with page.expect_response(
            lambda response: response.url == authorization_url
            and response.request.method == "POST"
        ) as save_response:
            page.locator('input[name="_save"]').click()

        self.assertEqual(save_response.value.status, 302)
        expect(page).to_have_url(
            self.live_reverse(
                "admin:authorizations_applicatie_change", args=(applicatie.pk,)
            )
        )

        expect(page.locator(".messagelist li")).to_have_count(0)
        expect(page.locator(".errornote")).to_have_count(0)
        expect(page.locator(".errorlist")).to_have_count(0)

        self.assertCountEqual(
            applicatie.autorisaties.values_list("component", "scopes"),
            [(ComponentTypes.ztc, [str(SCOPE_CATALOGI_READ)])],
        )
        self.assertEqual(page.page_errors(), [])
