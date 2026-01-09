# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
import os
import tempfile
from collections.abc import Callable

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from furl import furl
from playwright.sync_api import Browser, Playwright, sync_playwright

from openzaak.accounts.models import User

BROWSER_DRIVERS = {
    # keys for the E2E_DRIVER environment variable (likely from test matrix)
    "chromium": lambda p: p.chromium.launch(),
    "firefox": lambda p: p.firefox.launch(),
    "webkit": lambda p: p.webkit.launch(),
    "msedge": lambda p: p.chromium.launch(channel="msedge"),
    # MORE here, with interesting launch options
}
BROWSER_DEFAULT = "chromium"


def temp_media_root():
    # Convenience decorator/context manager to use a temporary directory as
    # PRIVATE_MEDIA_ROOT.
    tmpdir = tempfile.mkdtemp()
    return override_settings(MEDIA_ROOT=tmpdir)


def get_driver_name() -> str:
    return os.environ.get("E2E_DRIVER", BROWSER_DEFAULT)


@temp_media_root()
class PlaywrightSyncLiveServerTestCase(StaticLiveServerTestCase):
    """
    base class for convenient synchronous Playwright in Django

    to help with debugging set the environment variable PWDEBUG=1 or PWDEBUG=console

    to set the browser define E2E_DRIVER environment variable, with a value from the BROWSER_DRIVERS dictionary above.

    usage:

    from playwright.sync_api import expect

    class MyPageTest(PlaywrightSyncLiveServerTestCase):
        def test_my_page():
            # get a new context for test isolation
            context = self.browser.new_context()

            # open a page
            page = context.new_page()

            url = ...
            page.goto(url)

            # or more convenient:
            page.goto(self.live_url(path))
            page.goto(self.live_reverse("myapp:someobject_details", kwargs={"object_id": obj.id}, params={"query": "my keyword")))

            # do your things
            expect(page).to_have_title("Awesome title")
            ...
    """

    playwright: Playwright
    browser: Browser

    _old_async_unsafe: str

    @classmethod
    def launch_browser(cls, playwright: Playwright) -> Browser:
        launcher = cls.get_browser_launcher()
        return launcher(playwright)

    @classmethod
    def get_browser_launcher(cls) -> Callable[[Playwright], Browser]:
        name = get_driver_name()
        if name in BROWSER_DRIVERS:
            return BROWSER_DRIVERS[name]
        else:
            raise Exception(f"cannot find browser end-2-end driver '{name}'")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # required for playwright cleanup
        cls._old_async_unsafe = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        cls.playwright = sync_playwright().start()
        cls.browser = cls.launch_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        if cls._old_async_unsafe is None:
            os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE")
        else:
            os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = cls._old_async_unsafe

        super().tearDownClass()

        cls.browser.close()
        cls.playwright.stop()

    @classmethod
    def live_url(cls, path="/", star=False):
        """
        prepend self.live_server_url to path
        optionally append '*' wildcard matcher (useful for page.wait_for_url() etc)
        """
        url = f"{cls.live_server_url}{path}"
        if star:
            url = f"{url}*"
        return url

    @classmethod
    def live_reverse(cls, viewname, args=None, kwargs=None, params=None, star=False):
        """
        do a reverse() url, prepend self.live_server_url
        optionally add query params to url
        optionally append '*' wildcard matcher (useful for page.wait_for_url() etc)
        """
        path = reverse(viewname, args=args, kwargs=kwargs)
        assert not (params and star), "cannot combine params and star arguments (yet)"
        url = cls.live_url(path, star=star)
        if params:
            url = furl(url).set(params).url
        return url

    @classmethod
    def get_user_login_state(cls, user: User):
        assert user.pk, "user instance must be saved"

        context = cls.browser.new_context()
        page = context.new_page()

        page.goto(cls.live_reverse("admin:login"))

        page.fill("#id_auth-username", user.username)
        page.fill("#id_auth-password", "secret")

        page.get_by_role("button", name=_("Log in")).click()
        page.wait_for_url(cls.live_reverse("admin:index"))

        page.close()
        login_state = context.storage_state()
        context.close()
        return login_state
