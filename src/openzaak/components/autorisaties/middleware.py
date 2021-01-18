# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import List

from django.db import models
from django.db.models import Subquery

from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.middleware import (
    AuthMiddleware as _AuthMiddleware,
    JWTAuth as _JWTAuth,
)

from openzaak.utils.constants import COMPONENT_MAPPING


class JWTAuth(_JWTAuth):
    component = None

    def _request_auth(self) -> list:
        return []

    def get_autorisaties(self, init_component: str) -> models.QuerySet:
        """
        Retrieve all authorizations relevant to this component.
        """
        if not self.applicaties:
            return Autorisatie.objects.none()

        component = COMPONENT_MAPPING.get(init_component, init_component)
        app_ids = self.applicaties.values("id")
        return Autorisatie.objects.filter(
            applicatie_id__in=Subquery(app_ids), component=component
        )

    def has_auth(self, scopes: List[str], init_component: str = None, **fields) -> bool:
        if scopes is None:
            return False

        if not self.applicaties:
            return False

        # allow everything
        if self.applicaties.filter(heeft_alle_autorisaties=True).exists():
            return True

        if not init_component:
            return False

        autorisaties = self.get_autorisaties(init_component)
        scopes_provided = set()

        # filter on all additional components
        for field_name, field_value in fields.items():
            if hasattr(self, f"filter_{field_name}"):
                autorisaties = getattr(self, f"filter_{field_name}")(
                    autorisaties, field_value
                )
            else:
                autorisaties = self.filter_default(
                    autorisaties, field_name, field_value
                )

        for autorisatie in autorisaties:
            scopes_provided.update(autorisatie.scopes)

        return scopes.is_contained_in(list(scopes_provided))


class AuthMiddleware(_AuthMiddleware):
    header = "Authorization"

    def extract_jwt_payload(self, request):
        authorization = request.headers.get(self.header, "")
        prefix = f"{self.auth_type} "
        if authorization.startswith(prefix):
            # grab the actual token
            encoded = authorization[len(prefix) :]
        else:
            encoded = None

        request.jwt_auth = JWTAuth(encoded)
