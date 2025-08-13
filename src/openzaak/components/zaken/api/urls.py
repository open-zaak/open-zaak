# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from ..api.schema import custom_settings
from .viewsets import (
    DeprecatedReserveerZaakNummerViewSet,
    KlantContactViewSet,
    ReserveerZaakNummerViewSet,
    ResultaatViewSet,
    RolViewSet,
    StatusViewSet,
    SubStatusViewSet,
    ZaakAuditTrailViewSet,
    ZaakBesluitViewSet,
    ZaakBijwerkenViewset,
    ZaakContactMomentViewSet,
    ZaakEigenschapViewSet,
    ZaakInformatieObjectViewSet,
    ZaakNotitieViewSet,
    ZaakObjectViewSet,
    ZaakOpschortenViewset,
    ZaakRegistrerenViewset,
    ZaakVerlengenViewset,
    ZaakVerzoekViewSet,
    ZaakViewSet,
)

router = routers.DefaultRouter()
router.register(
    "zaken",
    ZaakViewSet,
    [
        routers.Nested("zaakeigenschappen", ZaakEigenschapViewSet),
        routers.Nested("audittrail", ZaakAuditTrailViewSet),
        routers.Nested("besluiten", ZaakBesluitViewSet),
    ],
)
router.register("statussen", StatusViewSet)
router.register("substatussen", SubStatusViewSet)
router.register("zaakobjecten", ZaakObjectViewSet)
router.register("klantcontacten", KlantContactViewSet)
router.register("rollen", RolViewSet)
router.register("resultaten", ResultaatViewSet)
router.register("zaakinformatieobjecten", ZaakInformatieObjectViewSet)
router.register("zaakcontactmomenten", ZaakContactMomentViewSet)
router.register("zaakverzoeken", ZaakVerzoekViewSet)
router.register("zaaknummer_reserveren", ReserveerZaakNummerViewSet)
router.register("zaaknotities", ZaakNotitieViewSet)

# XXX: alias for this endpoint, will be removed in 2.0
router.register(
    "reserveer_zaaknummer",
    DeprecatedReserveerZaakNummerViewSet,
    basename="zaakidentificatie_alias",
)
router.register("zaak_registreren", ZaakRegistrerenViewset, basename="registreerzaak")
zaakopschorten_view = ZaakOpschortenViewset.as_view({"post": "post"})
zaakbijwerken_view = ZaakBijwerkenViewset.as_view({"post": "post"})
zaakverlengen_view = ZaakVerlengenViewset.as_view({"post": "post"})


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
                path(
                    "zaak_opschorten/<uuid:uuid>",
                    zaakopschorten_view,
                    name="zaakopschorten",
                ),
                path(
                    "zaak_bijwerken/<uuid:uuid>",
                    zaakbijwerken_view,
                    name="zaakbijwerken",
                ),
                path(
                    "zaak_verlengen/<uuid:uuid>",
                    zaakverlengen_view,
                    name="verlengzaak",
                ),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
