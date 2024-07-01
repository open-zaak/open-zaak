# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.util import random_hex


class TOTPDeviceFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("openzaak.accounts.tests.factories.UserFactory")
    key = factory.LazyAttribute(lambda o: random_hex())

    class Meta:
        model = "otp_totp.TOTPDevice"


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    password = factory.PostGenerationMethodCall("set_password", "secret")

    class Params:
        with_totp_device = factory.Trait(
            device=factory.RelatedFactory(
                TOTPDeviceFactory,
                "user",
                name="default",
            )
        )

    class Meta:
        model = "accounts.User"


class SuperUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class RecoveryDeviceFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("openzaak.accounts.tests.factories.UserFactory")
    name = "backup"

    class Meta:
        model = StaticDevice


class RecoveryTokenFactory(factory.django.DjangoModelFactory):
    device = factory.SubFactory(RecoveryDeviceFactory)
    token = factory.LazyFunction(StaticToken.random_token)

    class Meta:
        model = StaticToken
