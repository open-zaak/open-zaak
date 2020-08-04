# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.conf import settings

from drf_yasg import openapi
from rest_framework import status
from vng_api_common.inspectors.view import AutoSchema as _AutoSchema
from vng_api_common.permissions import get_required_scopes
from vng_api_common.serializers import FoutSerializer

from .permissions import AuthRequired

logger = logging.getLogger(__name__)


COMMON_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: openapi.Response(
        "Unauthorized", schema=FoutSerializer
    ),
    status.HTTP_403_FORBIDDEN: openapi.Response("Forbidden", schema=FoutSerializer),
    status.HTTP_404_NOT_FOUND: openapi.Response("Not found", schema=FoutSerializer),
    status.HTTP_406_NOT_ACCEPTABLE: openapi.Response(
        "Not acceptable", schema=FoutSerializer
    ),
    status.HTTP_410_GONE: openapi.Response("Gone", schema=FoutSerializer),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: openapi.Response(
        "Unsupported media type", schema=FoutSerializer
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: openapi.Response(
        "Throttled", schema=FoutSerializer
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
        "Internal server error", schema=FoutSerializer
    ),
}


class AutoSchema(_AutoSchema):
    def get_security(self):
        """Return a list of security requirements for this operation.

        Returning an empty list marks the endpoint as unauthenticated (i.e. removes all accepted
        authentication schemes). Returning ``None`` will inherit the top-level secuirty requirements.

        :return: security requirements
        :rtype: list[dict[str,list[str]]]"""
        permissions = self.view.get_permissions()
        scope_permissions = [
            perm for perm in permissions if isinstance(perm, AuthRequired)
        ]

        if not scope_permissions:
            return super().get_security()

        if len(permissions) != len(scope_permissions):
            logger.warning(
                "Can't represent all permissions in OAS for path %s and method %s",
                self.path,
                self.method,
            )

        required_scopes = []
        for perm in scope_permissions:
            scopes = get_required_scopes(self.view)
            if scopes is None:
                continue
            required_scopes.append(scopes)

        if not required_scopes:
            return None  # use global security

        scopes = [str(scope) for scope in sorted(required_scopes)]

        # operation level security
        return [{settings.SECURITY_DEFINITION_NAME: scopes}]
