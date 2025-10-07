# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.views.generic import RedirectView

import structlog
from drf_spectacular.views import (
    SpectacularJSONAPIView as _SpectacularJSONAPIView,
    SpectacularYAMLAPIView as _SpectacularYAMLAPIView,
)

logger = structlog.stdlib.get_logger(__name__)


class AllowAllOriginsMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        return response


class SpectacularYAMLAPIView(AllowAllOriginsMixin, _SpectacularYAMLAPIView):
    """Spectacular YAML API view with Access-Control-Allow-Origin set to allow all"""


class SpectacularJSONAPIView(AllowAllOriginsMixin, _SpectacularJSONAPIView):
    """Spectacular JSON API view with Access-Control-Allow-Origin set to allow all"""


class DeprecationRedirectView(RedirectView):
    def get(self, request, *args, **kwargs):
        logger.warning(
            "deprecated_endpoint_called",
            endpoint="/api/v2/schema/openapi.yaml",
        )
        return super().get(request, *args, **kwargs)
