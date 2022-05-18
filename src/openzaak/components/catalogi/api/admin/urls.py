# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.urls import path

from .views import SelectielijstResultatenListView

app_name = "admin-api"

urlpatterns = [
    path(
        "selectielijst/resultaten",
        SelectielijstResultatenListView.as_view(),
        name="selectielijst-resultaten",
    ),
]
