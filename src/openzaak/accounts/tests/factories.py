# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.util import random_hex
from mozilla_django_oidc_db.constants import OIDC_ADMIN_CONFIG_IDENTIFIER
from mozilla_django_oidc_db.tests.factories import (
    OIDCClientFactory as BaseOIDCClientFactory,
    OIDCProviderFactory,
)

from openzaak.utils.tests.keycloak import KEYCLOAK_BASE_URL


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


class StaffUserFactory(UserFactory):
    is_staff = True


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


class OIDCClientFactory(BaseOIDCClientFactory):
    enabled = True

    class Params:  # pyright: ignore[reportIncompatibleVariableOverride]
        with_keycloak_provider = factory.Trait(
            oidc_provider=factory.SubFactory(
                OIDCProviderFactory,
                identifier="keycloak-provider",
                oidc_op_jwks_endpoint=f"{KEYCLOAK_BASE_URL}/certs",
                oidc_op_authorization_endpoint=f"{KEYCLOAK_BASE_URL}/auth",
                oidc_op_token_endpoint=f"{KEYCLOAK_BASE_URL}/token",
                oidc_op_user_endpoint=f"{KEYCLOAK_BASE_URL}/userinfo",
                oidc_op_logout_endpoint=f"{KEYCLOAK_BASE_URL}/logout",
            ),
            oidc_rp_client_id="testid",
            oidc_rp_client_secret="7DB3KUAAizYCcmZufpHRVOcD0TOkNO3I",
            oidc_rp_sign_algo="RS256",
        )
        with_admin = factory.Trait(
            identifier=OIDC_ADMIN_CONFIG_IDENTIFIER,
            oidc_rp_scopes_list=["email", "profile", "openid"],
        )
