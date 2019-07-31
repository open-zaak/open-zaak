from django.conf.urls import url
from django.urls import include, path

from vng_api_common import routers
from vng_api_common.schema import SchemaView

from .viewsets import (
    KlantContactViewSet, ResultaatViewSet, RolViewSet, StatusViewSet,
    ZaakAuditTrailViewSet, ZaakBesluitViewSet, ZaakEigenschapViewSet,
    ZaakInformatieObjectViewSet, ZaakObjectViewSet, ZaakViewSet
)

router = routers.DefaultRouter()
router.register('zaken', ZaakViewSet, [
    routers.nested('zaakeigenschappen', ZaakEigenschapViewSet),
    routers.nested('audittrail', ZaakAuditTrailViewSet),
    routers.nested('besluiten', ZaakBesluitViewSet),
])
router.register('statussen', StatusViewSet)
router.register('zaakobjecten', ZaakObjectViewSet)
router.register('klantcontacten', KlantContactViewSet)
router.register('rollen', RolViewSet)
router.register('resultaten', ResultaatViewSet)
router.register('zaakinformatieobjecten', ZaakInformatieObjectViewSet)


# TODO: the EndpointEnumerator seems to choke on path and re_path

urlpatterns = [
    url(r'^v(?P<version>\d+)/', include([

        # API documentation
        url(r'^schema/openapi(?P<format>\.json|\.yaml)$',
            SchemaView.without_ui(cache_timeout=None),
            name='schema-json'),
        url(r'^schema/$',
            SchemaView.with_ui('redoc', cache_timeout=None),
            name='schema-redoc'),

        # actual API
        url(r'^', include(router.urls)),

        # should not be picked up by drf-yasg
        path('', include('vng_api_common.api.urls')),
        path('', include('vng_api_common.notifications.api.urls')),
    ])),
]
