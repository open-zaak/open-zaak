# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf.urls import url
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from ..api.schema import custom_settings
from .viewsets import (
    BestandsDeelViewSet,
    EnkelvoudigInformatieObjectAuditTrailViewSet,
    EnkelvoudigInformatieObjectViewSet,
    GebruiksrechtenViewSet,
    ObjectInformatieObjectViewSet,
    VerzendingViewSet,
)

router = routers.DefaultRouter()
router.register(
    "enkelvoudiginformatieobjecten",
    EnkelvoudigInformatieObjectViewSet,
    [routers.nested("audittrail", EnkelvoudigInformatieObjectAuditTrailViewSet)],
    basename="enkelvoudiginformatieobject",
)
router.register("gebruiksrechten", GebruiksrechtenViewSet)
router.register("objectinformatieobjecten", ObjectInformatieObjectViewSet)
router.register("bestandsdelen", BestandsDeelViewSet)
router.register("verzendingen", VerzendingViewSet)


urlpatterns = [
    url(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml",
                    SpectacularAPIView.as_view(
                        urlconf="openzaak.components.documenten.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-documenten",
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(url_name="schema-documenten"),
                    name="schema-redoc-documenten",
                ),
                # actual API
                url(r"^", include(router.urls)),
                # should not be picked up by drf-yasg
                path("", router.APIRootView.as_view(), name="api-root-documenten"),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
