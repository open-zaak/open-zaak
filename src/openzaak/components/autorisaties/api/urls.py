# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from ..api.schema import custom_settings
from .viewsets import ApplicatieViewSet

router = routers.DefaultRouter()
router.register("applicaties", ApplicatieViewSet)


urlpatterns = [
    re_path(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml",
                    SpectacularAPIView.as_view(
                        urlconf="openzaak.components.autorisaties.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-autorisaties",
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(
                        url_name="schema-autorisaties", title=custom_settings["TITLE"]
                    ),
                    name="schema-redoc-autorisaties",
                ),
                # actual API
                path("", include(router.urls)),
                # should not be picked up by drf-yasg
                path("", router.APIRootView.as_view(), name="api-root-autorisaties"),
            ]
        ),
    )
]
