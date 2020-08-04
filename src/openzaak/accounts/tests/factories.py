# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")

    class Meta:
        model = "accounts.User"


class SuperUserFactory(UserFactory):
    is_staff = True
    is_superuser = True
