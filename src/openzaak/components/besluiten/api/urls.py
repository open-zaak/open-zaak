# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularRedocView
from vng_api_common import routers

from openzaak.utils.oas_extensions.views import (
    DeprecationRedirectView,
    SchemaDeprecationRedirectView,
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
)

from ..api.schema import custom_settings
from .viewsets import (
    BesluitAuditTrailViewSet,
    BesluitInformatieObjectViewSet,
    BesluitVerwerkenViewSet,
    BesluitViewSet,
)

router = routers.DefaultRouter()
router.register(
    "besluiten",
    BesluitViewSet,
    [routers.Nested("audittrail", BesluitAuditTrailViewSet)],
)
router.register("besluitinformatieobjecten", BesluitInformatieObjectViewSet)
router.register("besluit_verwerken", BesluitVerwerkenViewSet, basename="verwerkbesluit")


urlpatterns = [
    re_path(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml",
                    SchemaDeprecationRedirectView.as_view(
                        yaml_pattern="schema-besluiten-yaml",
                        json_pattern="schema-besluiten-json",
                    ),
                ),
                path(
                    "schema/openapi.json",
                    DeprecationRedirectView.as_view(
                        pattern_name="schema-besluiten-json"
                    ),
                ),
                path(
                    "openapi.yaml",
                    SpectacularYAMLAPIView.as_view(
                        urlconf="openzaak.components.besluiten.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-besluiten-yaml",
                ),
                path(
                    "openapi.json",
                    SpectacularJSONAPIView.as_view(
                        urlconf="openzaak.components.besluiten.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-besluiten-json",
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(
                        url_name="schema-besluiten-yaml", title=custom_settings["TITLE"]
                    ),
                    name="schema-redoc-besluiten",
                ),
                # actual API
                path("", include(router.urls)),
                # should not be picked up by drf-yasg
                path("", router.APIRootView.as_view(), name="api-root-besluiten"),
            ]
        ),
    )
]
