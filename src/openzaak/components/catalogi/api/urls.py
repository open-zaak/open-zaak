# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularRedocView
from vng_api_common import routers

from openzaak.utils.oas_extensions.views import (
    SchemaDeprecationRedirectView,
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
)

from ..api.schema import custom_settings
from .viewsets import (
    BesluitTypeViewSet,
    CatalogusViewSet,
    EigenschapViewSet,
    InformatieObjectTypeViewSet,
    ResultaatTypeViewSet,
    RolTypeViewSet,
    StatusTypeViewSet,
    ZaakObjectTypeViewSet,
    ZaakTypeInformatieObjectTypeViewSet,
    ZaakTypeViewSet,
)

router = routers.DefaultRouter()
router.register(r"catalogussen", CatalogusViewSet)
router.register(r"zaaktypen", ZaakTypeViewSet)
router.register(r"statustypen", StatusTypeViewSet)
router.register(r"eigenschappen", EigenschapViewSet)
router.register(r"roltypen", RolTypeViewSet)
router.register(r"informatieobjecttypen", InformatieObjectTypeViewSet)
router.register(r"besluittypen", BesluitTypeViewSet)
router.register(r"resultaattypen", ResultaatTypeViewSet)
router.register(r"zaaktype-informatieobjecttypen", ZaakTypeInformatieObjectTypeViewSet)
router.register(r"zaakobjecttypen", ZaakObjectTypeViewSet)


urlpatterns = [
    re_path(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml",
                    SchemaDeprecationRedirectView.as_view(
                        yaml_pattern="schema-catalogi-yaml",
                        json_pattern="schema-catalogi-json",
                    ),
                ),
                path(
                    "openapi.yaml",
                    SpectacularYAMLAPIView.as_view(
                        urlconf="openzaak.components.catalogi.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-catalogi-yaml",
                ),
                path(
                    "openapi.json",
                    SpectacularJSONAPIView.as_view(
                        urlconf="openzaak.components.catalogi.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-catalogi-json",
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(
                        url_name="schema-catalogi-yaml", title=custom_settings["TITLE"]
                    ),
                    name="schema-redoc-catalogi",
                ),
                # actual API
                path("", include(router.urls)),
                path("", router.APIRootView.as_view(), name="api-root-catalogi"),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
