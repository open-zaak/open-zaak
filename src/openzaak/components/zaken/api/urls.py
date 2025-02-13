# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from ..api.schema import custom_settings
from .viewsets import (
    KlantContactViewSet,
    ReserveerZaakNummerViewSet,
    ResultaatViewSet,
    RolViewSet,
    StatusViewSet,
    ZaakAuditTrailViewSet,
    ZaakBesluitViewSet,
    ZaakContactMomentViewSet,
    ZaakEigenschapViewSet,
    ZaakInformatieObjectViewSet,
    ZaakObjectViewSet,
    ZaakVerzoekViewSet,
    ZaakViewSet,
)

router = routers.DefaultRouter()
router.register(
    "zaken",
    ZaakViewSet,
    [
        routers.nested("zaakeigenschappen", ZaakEigenschapViewSet),
        routers.nested("audittrail", ZaakAuditTrailViewSet),
        routers.nested("besluiten", ZaakBesluitViewSet),
    ],
)
router.register("statussen", StatusViewSet)
router.register("zaakobjecten", ZaakObjectViewSet)
router.register("klantcontacten", KlantContactViewSet)
router.register("rollen", RolViewSet)
router.register("resultaten", ResultaatViewSet)
router.register("zaakinformatieobjecten", ZaakInformatieObjectViewSet)
router.register("zaakcontactmomenten", ZaakContactMomentViewSet)
router.register("zaakverzoeken", ZaakVerzoekViewSet)
router.register("reserveer_zaaknummer", ReserveerZaakNummerViewSet)

urlpatterns = [
    re_path(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml",
                    SpectacularAPIView.as_view(
                        urlconf="openzaak.components.zaken.api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-zaken",
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(
                        url_name="schema-zaken", title=custom_settings["TITLE"]
                    ),
                    name="schema-redoc-zaken",
                ),
                # actual API
                path("", include(router.urls)),
                path("", router.APIRootView.as_view(), name="api-root-zaken"),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
