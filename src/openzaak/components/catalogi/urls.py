from django.urls import include, path
from django.views.generic.base import TemplateView

from .views import DumpDataFixtureView, DumpDataView

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="catalogi/index.html"),
        name="main-catalogi",
    ),
    path("api/", include("openzaak.components.catalogi.api.urls")),
    path("data/", DumpDataView.as_view(), name="dumpdata"),
    path("data/fixture/", DumpDataFixtureView.as_view(), name="dumpdata-fixture"),
]
