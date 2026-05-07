# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django_webtest import WebTest

from openzaak.accounts.models import User


class AdminTestMixin:
    """
    Mixin to authenticate as a superuser for both Django TestCases and WebTest classes
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = User.objects.create_superuser(
            username="demo",
            email="demo@demo.com",
            password="demo",
            first_name="first",
            last_name="last",
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(user=self.user)

        if isinstance(self, WebTest):
            self.app.set_user(self.user)

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()
