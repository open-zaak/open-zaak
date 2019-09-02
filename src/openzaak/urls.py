from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView

from vng_api_common.views import ViewConfigView

handler500 = "openzaak.utils.views.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="main.html"), name="home"),
    path("view-config/", ViewConfigView.as_view(), name="view-config"),
    # separate apps
    re_path(
        r"^(?P<component>zaken|besluiten|documenten|authorizations)/$",
        TemplateView.as_view(template_name="index.html"),
        name="main",
    ),
    path("zaken/api/", include("openzaak.components.zaken.api.urls")),
    path("besluiten/api/", include("openzaak.components.besluiten.api.urls")),
    path("documenten/api/", include("openzaak.components.documenten.api.urls")),
    path("authorizations/api/", include("openzaak.components.authorizations.api.urls")),
    path("catalogi/", include("openzaak.components.catalogi.urls")),
    # Simply show the master template.
    path("ref/", include("vng_api_common.urls")),
    path("ref/", include("vng_api_common.notifications.urls")),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
urlpatterns += static(
    settings.PRIVATE_MEDIA_URL, document_root=settings.PRIVATE_MEDIA_ROOT
)

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
