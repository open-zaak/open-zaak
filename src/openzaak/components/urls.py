# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.urls import include, path

from openzaak import __version__

from .views import ComponentIndexView

BASE_NOTIFICATION_URL = (
    f"https://github.com/open-zaak/open-zaak/blob/{__version__}/src/notificaties.md"
)


urlpatterns = [
    # autorisaties
    path(
        "autorisaties/",
        ComponentIndexView.as_view(
            component="autorisaties",
            api_version="1",
            description="Autorisatie Component (AC)",
            notification_url="https://github.com/VNG-Realisatie/autorisaties-api/blob/1.0.1-alpha1/src/notificaties.md#autorisaties",
        ),
        name="index-autorisaties",
    ),
    path("autorisaties/api/", include("openzaak.components.autorisaties.api.urls")),
    # besluiten
    path(
        "besluiten/",
        ComponentIndexView.as_view(
            component="besluiten",
            api_version="1",
            description="Besluit Registratie Component (BRC)",
            notification_url=f"{BASE_NOTIFICATION_URL}#besluiten",
        ),
        name="index-besluiten",
    ),
    path("besluiten/api/", include("openzaak.components.besluiten.api.urls")),
    # catalogi
    path(
        "catalogi/",
        ComponentIndexView.as_view(
            component="catalogi",
            api_version="1",
            description="Zaaktype Catalogus (ZTC)",
            notification_url="https://github.com/VNG-Realisatie/catalogi-api/blob/stable/1.1.x/src/notificaties.md#catalogi",
        ),
        name="index-catalogi",
    ),
    path("catalogi/api/", include("openzaak.components.catalogi.api.urls")),
    # documenten
    path(
        "documenten/",
        ComponentIndexView.as_view(
            component="documenten",
            api_version="1",
            description="Documenten Registratie Component (DRC)",
            notification_url=f"{BASE_NOTIFICATION_URL}#documenten",
        ),
        name="index-documenten",
    ),
    path("documenten/api/", include("openzaak.components.documenten.api.urls")),
    # zaken
    path(
        "zaken/",
        ComponentIndexView.as_view(
            component="zaken",
            api_version="1",
            description="Zaak Registratie Component (ZRC)",
            notification_url=f"{BASE_NOTIFICATION_URL}#zaken",
        ),
        name="index-zaken",
    ),
    path("zaken/api/", include("openzaak.components.zaken.api.urls")),
]
