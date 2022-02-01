# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from typing import List, Union

from django.db import models
from django.utils.translation import gettext_lazy as _

import jwt
from rest_framework.exceptions import PermissionDenied
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.middleware import (
    AuthMiddleware as _AuthMiddleware,
    JWTAuth as _JWTAuth,
)

from openzaak.components.autorisaties.models import Role
from openzaak.utils.constants import COMPONENT_MAPPING


class JWTAuth(_JWTAuth):
    component = None

    @property
    def payload(self):
        try:
            return super().payload
        except jwt.PyJWTError as exc:
            raise PermissionDenied(
                _("JWT did not validate, try checking the `nbf` and `iat`"),
                code="jwt-{err}".format(err=type(exc).__name__.lower()),
            )

    @property
    def applicaties(self) -> Union[models.QuerySet, List, None]:
        # Add caching, compared to base class since we do a lot of self.applicaties calls
        if not hasattr(self, "_applicaties_qs"):
            self._applicaties_qs = super().applicaties
        return self._applicaties_qs

    @property
    def roles(self) -> models.QuerySet:
        role_slugs = self.payload.get("roles", [])
        return Role.objects.filter(slug__in=role_slugs)

    def get_roles(self, init_component: str) -> models.QuerySet:
        """
        Retrieve all authorizations relevant to this component.
        """
        if not self.roles:
            return Role.objects.none()

        component = COMPONENT_MAPPING.get(init_component, init_component)
        return Role.objects.filter(component=component)

    def _request_auth(self) -> list:
        return []

    def get_autorisaties(self, init_component: str) -> models.QuerySet:
        """
        Retrieve all authorizations relevant to this component.
        """
        if not self.applicaties:
            return Autorisatie.objects.none()

        component = COMPONENT_MAPPING.get(init_component, init_component)
        app_ids = [app.id for app in self.applicaties]
        return Autorisatie.objects.filter(
            applicatie_id__in=app_ids, component=component
        )

    def has_auth(self, scopes: List[str], init_component: str = None, **fields) -> bool:
        if scopes is None:
            return False

        if not self.applicaties:
            return False

        # allow everything
        superuser_applications = [
            app for app in self.applicaties if app.heeft_alle_autorisaties
        ]
        if any(superuser_applications):
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

        scopes_in_autorisaties = scopes.is_contained_in(list(scopes_provided))
        if not scopes_in_autorisaties:
            return False

        roles = self.get_roles(init_component)
        if not roles:
            return scopes_in_autorisaties

        scopes_provided_by_roles = set()

        # filter on all additional components
        for field_name, field_value in fields.items():
            if hasattr(self, f"filter_{field_name}"):
                roles = getattr(self, f"filter_{field_name}")(roles, field_value)
            else:
                roles = self.filter_default(roles, field_name, field_value)

        for role in roles:
            scopes_provided_by_roles.update(role.scopes)

        return scopes.is_contained_in(list(scopes_provided_by_roles))


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
