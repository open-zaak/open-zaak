# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import typing
from collections import OrderedDict
from typing import Dict, List, Type

from django.conf import settings

from drf_spectacular.openapi import AutoSchema as _AutoSchema
from drf_yasg import openapi
from rest_framework import exceptions, serializers, status
from vng_api_common.exceptions import PreconditionFailed
from vng_api_common.geo import GeoMixin
from vng_api_common.inspectors.view import (
    COMMON_ERRORS,
    DEFAULT_ACTION_ERRORS,
    HTTP_STATUS_CODE_TITLES,
    AutoSchema as _OldAutoSchema,
    ResponseRef,
    response_header,
)
from vng_api_common.permissions import get_required_scopes
from vng_api_common.serializers import FoutSerializer, ValidatieFoutSerializer
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


OLD_COMMON_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: use_ref,
    status.HTTP_403_FORBIDDEN: use_ref,
    status.HTTP_404_NOT_FOUND: use_ref,
    status.HTTP_406_NOT_ACCEPTABLE: use_ref,
    status.HTTP_410_GONE: use_ref,
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: use_ref,
    status.HTTP_429_TOO_MANY_REQUESTS: use_ref,
    status.HTTP_500_INTERNAL_SERVER_ERROR: use_ref,
}

COMMON_ERROR_STATUSES = [e.status_code for e in COMMON_ERRORS]
# error responses
COMMON_ERROR_RESPONSES = {status: FoutSerializer for status in COMMON_ERROR_STATUSES}
VALIDATION_ERROR_RESPONSES = {status.HTTP_400_BAD_REQUEST: ValidatieFoutSerializer}
FILE_ERROR_RESPONSES = {status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: FoutSerializer}
PRECONDITION_ERROR_RESPONSES = {status.HTTP_412_PRECONDITION_FAILED: FoutSerializer}


class OldAutoSchema(_OldAutoSchema):
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

    def should_filter(self) -> bool:
        """
        support expand for detail views
        """
        include_allowed = getattr(self.view, "include_allowed", lambda: False)()
        if self.method == "GET" and include_allowed:
            return True

        return super().should_page()


class AutoSchema(_AutoSchema):
    def get_auth(self) -> List[Dict[str, List[str]]]:
        """
        Return a list of security requirements for this operation.

        `OpenApiAuthenticationExtension` can't be used here since it's tightly coupled
        with DRF authentication classes, and we have none in Open Zaak
        """
        permissions = self.view.get_permissions()
        scope_permissions = [
            perm for perm in permissions if isinstance(perm, AuthRequired)
        ]

        if not scope_permissions:
            return super().get_auth()

        scopes = get_required_scopes(self.view.request, self.view)
        if not scopes:
            return []

        return [{settings.SECURITY_DEFINITION_NAME: [str(scopes)]}]

    def get_error_responses(self) -> Dict[int, Type[serializers.Serializer]]:
        """
        return dictionary of error codes and correspondent error serializers
        - define status codes based on exceptions for each endpoint
        - define error serialzers based on status code
        """

        # only supports viewsets
        action = getattr(self.view, "action")
        if not action:
            return {}

        # define status codes for the action based on potential exceptions
        # general errors
        general_klasses = DEFAULT_ACTION_ERRORS.get(action)
        if general_klasses is None:
            logger.debug("Unknown action %s, no default error responses added")
            return {}

        exception_klasses = general_klasses[:]
        # add geo and validation errors
        has_validation_errors = action == "list" or any(
            issubclass(klass, exceptions.ValidationError) for klass in exception_klasses
        )
        if has_validation_errors:
            exception_klasses.append(exceptions.ValidationError)

        if isinstance(self.view, GeoMixin):
            exception_klasses.append(PreconditionFailed)

        status_codes = sorted({e.status_code for e in exception_klasses})

        # choose serializer based on the status code
        responses = {}
        for status_code in status_codes:
            error_serializer = (
                ValidatieFoutSerializer
                if status_code == exceptions.ValidationError.status_code
                else FoutSerializer
            )
            responses[status_code] = error_serializer

        return responses

    def get_response_serializers(self) -> Dict[int, Type[serializers.Serializer]]:
        """append error serializers"""
        response_serializers = super().get_response_serializers()

        if self.method == "DELETE":
            status_code = 204
            serializer = None
        elif self._is_create_operation():
            status_code = 201
            serializer = response_serializers
        else:
            status_code = 200
            serializer = response_serializers

        responses = {
            status_code: serializer,
            **self.get_error_responses(),
        }
        return responses

    def _get_response_for_code(
        self, serializer, status_code, media_types=None, direction="response"
    ):
        """choose media types and set descriptions"""
        if not media_types:
            if int(status_code) >= 400:
                media_types = [ERROR_CONTENT_TYPE]
            else:
                media_types = ["application/json"]

        response = super()._get_response_for_code(
            serializer, status_code, media_types, direction="response"
        )

        # add description based on the status code
        if not response.get("description"):
            response["description"] = HTTP_STATUS_CODE_TITLES.get(int(status_code), "")
        return response

    def get_request_serializer(self) -> typing.Any:
        """Build custom request serializer for Search endpoints"""
        request_serializer = super().get_request_serializer()

        action = getattr(self.view, "action")
        if not action:
            return request_serializer

        if not getattr(getattr(self.view, action, ""), "is_search_action", False):
            return request_serializer

        filter_params = self._get_filter_parameters()
        search_input_serializer = self.view.search_input_serializer_class
        schema = self._map_serializer(search_input_serializer, "request")
        # add query params to request body schema
        for filter_param in filter_params:
            property = filter_param["schema"]
            property["description"] = filter_param.get("description")
            schema["properties"][filter_param["name"]] = property

        return {"application/json": schema}

    def _get_paginator(self):
        """
        support dynamic pagination_class in view.paginator method
        """
        if hasattr(self.view, "paginator"):
            return self.view.paginator

        return super()._get_paginator()
