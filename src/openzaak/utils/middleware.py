import logging
from typing import Dict, Optional

from django.conf import settings
from django.http import HttpRequest

from rest_framework.response import Response
from rest_framework.reverse import reverse
from vng_api_common.middleware import (
    VERSION_HEADER,
    APIVersionHeaderMiddleware as _APIVersionHeaderMiddleware,
)

logger = logging.getLogger(__name__)


class LogHeadersMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        self.log(request)
        return self.get_response(request) if self.get_response else None

    def log(self, request: HttpRequest):
        logger.debug("Request headers for %s: %r", request.path, request.headers)


def get_version_mapping() -> Dict[str, str]:
    apis = ("autorisaties", "besluiten", "catalogi", "documenten", "zaken")
    version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]

    return {
        reverse(f"api-root-{api}", kwargs={"version": version}): getattr(
            settings, f"{api.upper()}_API_VERSION"
        )
        for api in apis
    }


class APIVersionHeaderMiddleware(_APIVersionHeaderMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.version_mapping = get_version_mapping()

    def __call__(self, request):
        if self.get_response is None:
            return None

        response = self.get_response(request)

        # not an API response, exit early
        if not isinstance(response, Response):
            return response

        # set the header
        version = self._get_version(request.path)
        if version is not None:
            response[VERSION_HEADER] = version

        return response

    def _get_version(self, path: str) -> Optional[str]:
        for prefix, version in self.version_mapping.items():
            if path.startswith(prefix):
                return version
        return None
