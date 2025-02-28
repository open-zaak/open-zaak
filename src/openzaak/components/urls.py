# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.urls import include, path

from openzaak import __version__

from .views import ComponentIndexView

urlpatterns = [
    # autorisaties
    path(
        "autorisaties/",
        ComponentIndexView.as_view(component="autorisaties", github_ref="1.0.1-alpha1"),
        name="index-autorisaties",
    ),
    path("autorisaties/api/", include("openzaak.components.autorisaties.api.urls")),
    # besluiten
    path(
        "besluiten/",
        ComponentIndexView.as_view(
            component="besluiten",
            repository="https://github.com/open-zaak/open-zaak",
            github_ref=__version__,
        ),
        name="index-besluiten",
    ),
    path("besluiten/api/", include("openzaak.components.besluiten.api.urls")),
    # catalogi
    path(
        "catalogi/",
        ComponentIndexView.as_view(component="catalogi", github_ref="stable/1.1.x"),
        name="index-catalogi",
    ),
    path("catalogi/api/", include("openzaak.components.catalogi.api.urls")),
    # documenten
    path(
        "documenten/",
        ComponentIndexView.as_view(
            component="documenten",
            repository="https://github.com/open-zaak/open-zaak",
            github_ref=__version__,
        ),
        name="index-documenten",
    ),
    path("documenten/api/", include("openzaak.components.documenten.api.urls")),
    # zaken
    path(
        "zaken/",
        ComponentIndexView.as_view(
            component="zaken",
            repository="https://github.com/open-zaak/open-zaak",
            github_ref=__version__,
        ),
        name="index-zaken",
    ),
    path("zaken/api/", include("openzaak.components.zaken.api.urls")),
]
