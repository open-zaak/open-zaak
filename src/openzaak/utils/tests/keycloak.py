# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from contextlib import contextmanager
from unittest.mock import patch

from django.apps import apps

KEYCLOAK_BASE_URL = "http://localhost:8080/realms/test/protocol/openid-connect"


@contextmanager
def mock_oidc_db_config(app_label: str, model: str, **overrides):
    """
    Bundle all the required mocks.

    This context manager deliberately prevents the mocked things from being injected in
    the test method signature.
    """
    defaults = {
        "enabled": True,
        "oidc_rp_client_id": "testid",
        "oidc_rp_client_secret": "7DB3KUAAizYCcmZufpHRVOcD0TOkNO3I",
        "oidc_rp_sign_algo": "RS256",
        "oidc_rp_scopes_list": ["openid"],
        "oidc_op_jwks_endpoint": f"{KEYCLOAK_BASE_URL}/certs",
        "oidc_op_authorization_endpoint": f"{KEYCLOAK_BASE_URL}/auth",
        "oidc_op_token_endpoint": f"{KEYCLOAK_BASE_URL}/token",
        "oidc_op_user_endpoint": f"{KEYCLOAK_BASE_URL}/userinfo",
    }
    field_values = {**defaults, **overrides}
    model_cls = apps.get_model(app_label, model)
    with (
        # bypass django-solo queries + cache hits
        patch(
            f"{model_cls.__module__}.{model}.get_solo",
            return_value=model_cls(**field_values),
        ),
        # mock the state & nonce random value generation so we get predictable URLs to
        # match with VCR
        patch(
            "mozilla_django_oidc.views.get_random_string",
            return_value="not-a-random-string",
        ),
    ):
        yield
