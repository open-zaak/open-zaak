# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView

from openzaak.utils.views import ViewConfigView

handler500 = "openzaak.utils.views.server_error"

urlpatterns = [
    path("admin/config/", include("openzaak.config.admin_urls")),
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="main.html"), name="home"),
    path("view-config/", ViewConfigView.as_view(), name="view-config"),
    # separate apps
    re_path(
        r"^(?P<component>zaken|besluiten|documenten|autorisaties|catalogi)/$",
        TemplateView.as_view(template_name="index.html"),
        name="main",
    ),
    path("zaken/api/", include("openzaak.components.zaken.api.urls")),
    path("besluiten/api/", include("openzaak.components.besluiten.api.urls")),
    path("documenten/api/", include("openzaak.components.documenten.api.urls")),
    path("autorisaties/api/", include("openzaak.components.autorisaties.api.urls")),
    path("catalogi/api/", include("openzaak.components.catalogi.api.urls")),
    # Simply show the master template.
    path("ref/", include("vng_api_common.urls")),
    path("ref/", include("vng_api_common.notifications.urls")),
    # auth backends
    path("adfs/", include("django_auth_adfs.urls")),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
urlpatterns += static(
    settings.PRIVATE_MEDIA_URL, document_root=settings.PRIVATE_MEDIA_ROOT
)

if apps.is_installed("debug_toolbar"):
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]


if apps.is_installed("silk"):
    urlpatterns += [path(r"silk/", include("silk.urls", namespace="silk"))]
