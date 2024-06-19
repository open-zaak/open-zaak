# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from ..api.schema import custom_settings
from .viewsets import (
    BestandsDeelViewSet,
    EnkelvoudigInformatieObjectAuditTrailViewSet,
    EnkelvoudigInformatieObjectImportDestroyView,
    EnkelvoudigInformatieObjectImportReportView,
    EnkelvoudigInformatieObjectImportStatusView,
    EnkelvoudigInformatieObjectImportUploadView,
    EnkelvoudigInformatieObjectImportView,
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

import_patterns = [
    path(
        "create",
        EnkelvoudigInformatieObjectImportView.as_view(
            {"post": "create"}, name="create"
        ),
        name="create",
    ),
    path(
        "<uuid:uuid>/upload",
        EnkelvoudigInformatieObjectImportUploadView.as_view(
            {"post": "create"}, name="upload"
        ),
        name="upload",
    ),
    path(
        "<uuid:uuid>/status",
        EnkelvoudigInformatieObjectImportStatusView.as_view(
            {"get": "retrieve"}, name="status"
        ),
        name="status",
    ),
    path(
        "<uuid:uuid>/report",
        EnkelvoudigInformatieObjectImportReportView.as_view(
            {"get": "retrieve"}, name="report"
        ),
        name="report",
    ),
    path(
        "<uuid:uuid>/delete",
        EnkelvoudigInformatieObjectImportDestroyView.as_view(
            {"delete": "destroy"}, name="destroy"
        ),
        name="destroy",
    ),
]

urlpatterns = [
    re_path(
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
                    SpectacularRedocView.as_view(
                        url_name="schema-documenten", title=custom_settings["TITLE"]
                    ),
                    name="schema-redoc-documenten",
                ),
                # actual API
                path("", include(router.urls)),
                path(
                    "import/",
                    include(
                        (import_patterns, "openzaak.components.documenten"),
                        namespace="documenten-import",
                    ),
                ),
                path("", router.APIRootView.as_view(), name="api-root-documenten"),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
