from django.conf import settings
from django.conf.urls import url
from django.urls import include, path

from vng_api_common import routers
from vng_api_common.schema import SchemaView as _SchemaView

from .viewsets import ApplicatieViewSet

router = routers.DefaultRouter()
router.register('applicaties', ApplicatieViewSet)


# set the path to schema file
class SchemaView(_SchemaView):
    schema_path = settings.SPEC_URL['authorizations']


urlpatterns = [
    url(r'^v(?P<version>\d+)/', include([

        # API documentation
        url(r'^schema/openapi(?P<format>\.json|\.yaml)$',
            SchemaView.without_ui(cache_timeout=None),
            name='schema-json-authorizations'),
        url(r'^schema/$',
            SchemaView.with_ui('redoc', cache_timeout=None),
            name='schema-redoc-authorizations'),

        # actual API
        url(r'^', include(router.urls)),

        # should not be picked up by drf-yasg
        path('', include('vng_api_common.api.urls')),
    ])),
]
