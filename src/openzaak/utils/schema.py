# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from collections import OrderedDict

from django.conf import settings

from drf_yasg import openapi
from rest_framework import status
from vng_api_common.inspectors.view import (
    AutoSchema as _AutoSchema,
    ResponseRef,
    response_header,
)
from vng_api_common.permissions import get_required_scopes
from vng_api_common.views import ERROR_CONTENT_TYPE

from .middleware import WARNING_HEADER
from .permissions import AuthRequired

logger = logging.getLogger(__name__)

warning_header = response_header(
    "Geeft een endpoint-specifieke waarschuwing, zoals het uitfaseren van functionaliteit.",
    type=openapi.TYPE_STRING,
)


class use_ref:
    pass


COMMON_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: use_ref,
    status.HTTP_403_FORBIDDEN: use_ref,
    status.HTTP_404_NOT_FOUND: use_ref,
    status.HTTP_406_NOT_ACCEPTABLE: use_ref,
    status.HTTP_410_GONE: use_ref,
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: use_ref,
    status.HTTP_429_TOO_MANY_REQUESTS: use_ref,
    status.HTTP_500_INTERNAL_SERVER_ERROR: use_ref,
}


class AutoSchema(_AutoSchema):
    def get_response_schemas(self, response_serializers):
        # parent class doesn't support the `use_ref` singleton - we convert them to
        # ResponseRef instances
        for status_code, serializer in response_serializers.items():
            if serializer is use_ref:
                response_serializers[status_code] = ResponseRef(
                    self.components, str(status_code)
                )

        responses = super().get_response_schemas(response_serializers)

        if not hasattr(self.view, "deprecation_message"):
            return responses

        for status_code, response in responses.items():
            if not isinstance(response, ResponseRef):
                response.setdefault("headers", OrderedDict())
                response["headers"][WARNING_HEADER] = warning_header

        return responses

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
            scopes = get_required_scopes(None, self.view)
            if scopes is None:
                continue
            required_scopes.append(scopes)

        if not required_scopes:
            return None  # use global security

        scopes = [str(scope) for scope in sorted(required_scopes)]

        # operation level security
        return [{settings.SECURITY_DEFINITION_NAME: scopes}]

    def get_produces(self):
        """
        Remove the application/problem+json content type.

        Workaround - these are patched in afterwards. The produce values depends on the
        context, which is not supported in OpenAPI 2.0.x.
        """
        produces = super().get_produces()

        # patched in after the conversion of OAS 2.0 -> OAS 3.0
        if ERROR_CONTENT_TYPE in produces:
            produces.remove(ERROR_CONTENT_TYPE)

        return produces

    def is_deprecated(self):
        deprecation_message = getattr(self.view, "deprecation_message", None)
        return bool(deprecation_message) or super().is_deprecated()

    def get_default_responses(self) -> OrderedDict:
        """
        Workaround for EnkelvoudigInformatieObject/_zoek endpoint, which can't be marked as `is_search_action`
        But still needs pagination
        """
        if self._is_page_view:
            return self._get_search_responses()

        return super().get_default_responses()

    def should_page(self):
        """
        Workaround for EnkelvoudigInformatieObject/_zoek endpoint, which can't be marked as `is_search_action`
        But still needs pagination
        """
        if self._is_page_view:
            return hasattr(self.view, "paginator")

        return super().should_page()

    @property
    def _is_page_view(self) -> bool:
        if not getattr(self.view, "action", None):
            return False

        action = getattr(self.view, self.view.action)
        return getattr(action, "is_page_action", False)
