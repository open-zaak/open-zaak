# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from openzaak.accounts.models import User


class AdminTestMixin:
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

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()
