# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import TemplateView

from maykin_2fa import monkeypatch_admin
from maykin_2fa.urls import urlpatterns, webauthn_urlpatterns
from mozilla_django_oidc_db.views import AdminLoginFailure
from vng_api_common.views import ScopesView

from openzaak.accounts.views import QRGeneratorView
from openzaak.utils.exceptions import RequestEntityTooLargeException
from openzaak.utils.views import ErrorDocumentView, ViewConfigView

admin.site.enable_nav_sidebar = False

handler500 = "maykin_common.views.server_error"

# Configure admin
monkeypatch_admin()


urlpatterns = [
    path("admin/config/", include("openzaak.config.admin_urls")),
    path(
        "admin/api/v1/catalogi/", include("openzaak.components.catalogi.api.admin.urls")
    ),
    path("admin/login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    # 2fa
    # See https://github.com/maykinmedia/open-api-framework/issues/40
    # and https://github.com/maykinmedia/open-api-framework/issues/59
    # Temporary workaround to remove the dependency on `django.contrib.sites` when
    # generating the app label for 2FA. This should be removed once `sites` are removed
    path("admin/mfa/qrcode/", QRGeneratorView.as_view(), name="qr"),
    path("admin/", include((urlpatterns, "maykin_2fa"))),
    path("admin/", include((webauthn_urlpatterns, "two_factor"))),
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="main.html"), name="home"),
    # separate apps per component
    path("", include("openzaak.components.urls")),
    path("view-config/", ViewConfigView.as_view(), name="view-config"),
    # override view with a new template, based on maykin-common
    path(
        "ref/scopes/",
        ScopesView.as_view(template_name="scopes.html"),
        name="scopes",
    ),
    path("ref/", include("vng_api_common.urls")),
    path("ref/", include("notifications_api_common.urls")),
    # auth backends
    path("oidc/", include("mozilla_django_oidc.urls")),
    # custom error documents for nginx
    path(
        "413.json",
        ErrorDocumentView.as_view(exception_cls=RequestEntityTooLargeException),
        name="errordoc-413",
    ),
    path("500.json", ErrorDocumentView.as_view(), name="errordoc-500"),
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
