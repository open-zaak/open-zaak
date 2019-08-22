from django.conf import settings
from django.conf.urls import url
from django.urls import include, path

from vng_api_common import routers
from vng_api_common.schema import SchemaView as _SchemaView

from .views import (
    BesluitTypeViewSet,
    CatalogusViewSet,
    EigenschapViewSet,
    InformatieObjectTypeViewSet,
    ResultaatTypeViewSet,
    RolTypeViewSet,
    StatusTypeViewSet,
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


# set the path to schema file
class SchemaView(_SchemaView):
    schema_path = settings.SPEC_URL["catalogi"]


urlpatterns = [
    url(
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                url(
                    r"^schema/openapi(?P<format>\.json|\.yaml)$",
                    SchemaView.without_ui(cache_timeout=None),
                    name="schema-json-catalogi",
                ),
                url(
                    r"^schema/$",
                    SchemaView.with_ui("redoc", cache_timeout=None),
                    name="schema-redoc-catalogi",
                ),
                # actual API
                url(r"^", include(router.urls)),
                # should not be picked up by drf-yasg
                path("", include("vng_api_common.api.urls")),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
