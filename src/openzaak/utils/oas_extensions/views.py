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


class DeprecationRedirectView(RedirectView):  # pragma: no cover
    def get(self, request, *args, **kwargs):
        logger.warning(
            "deprecated_endpoint_called",
            endpoint=request.path,
        )
        return super().get(request, *args, **kwargs)


class SchemaDeprecationRedirectView(DeprecationRedirectView):  # pragma: no cover
    yaml_pattern = None
    json_pattern = None

    def get(self, request, *args, **kwargs):
        if request.GET.get("format") == "json":
            self.pattern_name = self.json_pattern
        else:
            self.pattern_name = self.yaml_pattern

        return super().get(request, *args, **kwargs)
