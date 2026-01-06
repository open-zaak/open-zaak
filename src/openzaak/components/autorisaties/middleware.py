# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import List, Union
from urllib.parse import urlparse

from django.db import models

from django_loose_fk.loaders import get_loader_class
from django_loose_fk.utils import get_resource_for_path
from vng_api_common.authorizations.middleware import (
    AuthMiddleware as _AuthMiddleware,
    JWTAuth as _JWTAuth,
)
from vng_api_common.authorizations.models import Autorisatie

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.utils.constants import COMPONENT_MAPPING

loader = get_loader_class()()


class JWTAuth(_JWTAuth):
    component = None

    @property
    def applicaties(self) -> Union[models.QuerySet, List, None]:
        # Add caching, compared to base class since we do a lot of self.applicaties calls
        if not hasattr(self, "_applicaties_qs"):
            self._applicaties_qs = super().applicaties
        return self._applicaties_qs

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

    def get_catalogus_autorisaties(self, init_component: str) -> models.QuerySet:
        """
        Retrieve all CatalogusAutorisaties relevant to this component.
        Cache per component to avoid duplicate queries.
        """
        if not self.applicaties:
            return CatalogusAutorisatie.objects.none()

        # initialize cache dict if not present
        if not hasattr(self, "_catalogus_cache"):
            self._catalogus_cache = {}

        if init_component not in self._catalogus_cache:
            component = COMPONENT_MAPPING.get(init_component, init_component)
            app_ids = [app.id for app in self.applicaties]
            qs = (
                CatalogusAutorisatie.objects.filter(
                    applicatie_id__in=app_ids, component=component
                )
                .select_related("catalogus")
                .prefetch_related(
                    "catalogus__zaaktype_set",
                    "catalogus__informatieobjecttype_set",
                    "catalogus__besluittype_set",
                )
            )
            self._catalogus_cache[init_component] = qs

        return self._catalogus_cache[init_component]

    def has_auth(
        self, scopes: List[str], component: str | None = None, **fields
    ) -> bool:
        if scopes is None:
            return False

        if not self.applicaties:
            return False

        # allow everything
        if self.has_alle_autorisaties:
            return True

        if not component:
            return False

        autorisaties = self.get_autorisaties(component)
        catalogus_autorisaties = self.get_catalogus_autorisaties(component)
        has_catalogus_autorisaties = catalogus_autorisaties.exists()
        scopes_provided = set()

        # filter on all additional components
        for field_name, field_value in fields.items():
            if hasattr(self, f"filter_{field_name}"):
                autorisaties = getattr(self, f"filter_{field_name}")(
                    autorisaties, field_value
                )
                if has_catalogus_autorisaties:
                    catalogus_autorisaties = getattr(self, f"filter_{field_name}")(
                        catalogus_autorisaties, field_value
                    )
            else:
                autorisaties = self.filter_default(
                    autorisaties, field_name, field_value
                )
                if (
                    has_catalogus_autorisaties
                    and field_value
                    and loader.is_local_url(field_value)
                ):
                    resolved = get_resource_for_path(urlparse(field_value).path)
                    catalogus_autorisaties = self.filter_default(
                        catalogus_autorisaties, "catalogus", resolved.catalogus
                    )

        for autorisatie in autorisaties:
            scopes_provided.update(autorisatie.scopes)

        for catalogus_autorisatie in catalogus_autorisaties:
            scopes_provided.update(catalogus_autorisatie.scopes)

        return scopes.is_contained_in(list(scopes_provided))

    @property
    def has_alle_autorisaties(self) -> bool:
        if not self.applicaties:
            return False

        superuser_applications = [
            app for app in self.applicaties if app.heeft_alle_autorisaties
        ]
        return any(superuser_applications)


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
