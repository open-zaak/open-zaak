# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import typing
from typing import Dict, List, Optional, Type

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import (
    AutoSchema as _AutoSchema,
    ResolvedComponent,
    append_meta,
    build_array_type,
    build_object_type,
    is_list_serializer,
)
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes
from furl import furl
from rest_framework import exceptions, serializers, status
from vng_api_common.caching.introspection import has_cache_header
from vng_api_common.constants import HEADER_AUDIT, HEADER_LOGRECORD_ID, VERSION_HEADER
from vng_api_common.exceptions import PreconditionFailed
from vng_api_common.geo import DEFAULT_CRS, HEADER_ACCEPT, HEADER_CONTENT, GeoMixin
from vng_api_common.permissions import get_required_scopes
from vng_api_common.schema import (
    COMMON_ERRORS,
    DEFAULT_ACTION_ERRORS,
    HTTP_STATUS_CODE_TITLES,
    _view_supports_audittrail,
)
from vng_api_common.serializers import FoutSerializer, ValidatieFoutSerializer
from vng_api_common.views import ERROR_CONTENT_TYPE

from .expansion import EXPAND_KEY
from .mixins import ExpandMixin
from .permissions import AuthRequired

logger = logging.getLogger(__name__)


COMMON_ERROR_STATUSES = [e.status_code for e in COMMON_ERRORS]
# error responses
COMMON_ERROR_RESPONSES = {status: FoutSerializer for status in COMMON_ERROR_STATUSES}
VALIDATION_ERROR_RESPONSES = {status.HTTP_400_BAD_REQUEST: ValidatieFoutSerializer}
FILE_ERROR_RESPONSES = {status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: FoutSerializer}
PRECONDITION_ERROR_RESPONSES = {status.HTTP_412_PRECONDITION_FAILED: FoutSerializer}


def get_component_from_serializer(serializer: serializers.Serializer) -> str:
    return serializer.Meta.model._meta.app_label


def get_external_schema_ref(serializer: serializers.Serializer) -> str:
    """
    Constructs the schema references for external resource
    """
    component = get_component_from_serializer(serializer)
    oas_url = settings.EXTERNAL_API_MAPPING[component].oas_url
    resource_name = serializer.Meta.model._meta.object_name

    f = furl(oas_url)
    f.fragment.path = f"/components/schemas/{resource_name}"
    return f.url


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

    def get_operation_id(self):
        """
        Use view basename as a base for operation_id
        """
        if hasattr(self.view, "basename"):
            basename = self.view.basename
            action = "head" if self.method == "HEAD" else self.view.action
            # make compatible with old OAS
            if action == "destroy":
                action = "delete"
            elif action == "retrieve":
                action = "read"

            return f"{basename}_{action}"
        return super().get_operation_id()

    def get_error_responses(self) -> Dict[int, Type[serializers.Serializer]]:
        """
        return dictionary of error codes and correspondent error serializers
        - define status codes based on exceptions for each endpoint
        - define error serializers based on status code
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

    def get_response_serializers(
        self,
    ) -> Dict[int, Optional[Type[serializers.Serializer]]]:
        """append error serializers"""
        response_serializers = super().get_response_serializers()

        if self.method == "HEAD":
            return {200: None}

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
        """
        choose media types and set descriptions
        add custom response for expand
        """
        if not media_types:
            if int(status_code) >= 400:
                media_types = [ERROR_CONTENT_TYPE]
            else:
                media_types = ["application/json"]

        response = super()._get_response_for_code(
            serializer, status_code, media_types, direction
        )

        if 200 <= int(status_code) < 300 and isinstance(self.view, ExpandMixin):
            response = self.get_expand_response(serializer, response, direction)

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

    def get_expand_response(self, serializer, base_response, direction):
        """
        add '_expand' into response schema
        """

        include_allowed = getattr(self.view, "include_allowed", lambda: False)()
        base_serializer = (
            serializer.child if is_list_serializer(serializer) else serializer
        )
        inclusion_serializers = getattr(base_serializer, "inclusion_serializers", {})

        if not include_allowed or not inclusion_serializers:
            return base_response

        response = base_response.copy()
        # rewrite schema from response
        expand_properties = {}
        for name, serializer_class in inclusion_serializers.items():
            # create schema for top-level inclusions for now
            if "." in name:
                continue

            inclusion_field = base_serializer.fields[name]
            meta = self._get_serializer_field_meta(inclusion_field, direction)
            inclusion_serializer = import_string(serializer_class)

            if get_component_from_serializer(
                base_serializer
            ) == get_component_from_serializer(inclusion_serializer):
                # same component - local ref
                inclusion_ref = self.resolve_serializer(
                    inclusion_serializer, direction
                ).ref
            else:
                # external component - external ref
                inclusion_ref = {"$ref": get_external_schema_ref(inclusion_serializer)}

            many = True if hasattr(inclusion_field, "child_relation") else False
            if many:
                inclusion_schema = append_meta(build_array_type(inclusion_ref), meta)
            else:
                inclusion_schema = append_meta(inclusion_ref, meta)

            expand_properties[name] = inclusion_schema

        inclusions_schema = build_object_type(
            properties=expand_properties,
            description=_(
                "Display details of the linked resources requested in the `expand` parameter"
            ),
        )
        base_component = self.resolve_serializer(base_serializer, direction)
        expand_component_name = f"Expand{base_component.name}"
        expand_component = ResolvedComponent(
            name=expand_component_name,
            type=ResolvedComponent.SCHEMA,
            object=expand_component_name,
            schema={
                "allOf": [
                    base_component.ref,
                    build_object_type(properties={EXPAND_KEY: inclusions_schema}),
                ]
            },
        )
        self.registry.register_on_missing(expand_component)
        expand_schema = expand_component.ref

        # paginate if needed
        if self._is_list_view(serializer):
            expand_schema = build_array_type(expand_schema)

            paginator = self._get_paginator()
            if paginator:
                paginated_name = self.get_paginated_name(expand_component_name)
                paginated_component = ResolvedComponent(
                    name=paginated_name,
                    type=ResolvedComponent.SCHEMA,
                    schema=paginator.get_paginated_response_schema(expand_schema),
                    object=paginated_name,
                )
                self.registry.register_on_missing(paginated_component)
                expand_schema = paginated_component.ref

        response["content"]["application/json"]["schema"] = expand_schema

        return response

    def get_override_parameters(self):
        """Add request and response headers"""
        version_headers = self.get_version_headers()
        content_type_headers = self.get_content_type_headers()
        cache_headers = self.get_cache_headers()
        log_headers = self.get_log_headers()
        location_headers = self.get_location_headers()
        geo_headers = self.get_geo_headers()
        return (
            version_headers
            + content_type_headers
            + cache_headers
            + log_headers
            + location_headers
            + geo_headers
        )

    def get_version_headers(self) -> List[OpenApiParameter]:
        return [
            OpenApiParameter(
                name=VERSION_HEADER,
                type=str,
                location=OpenApiParameter.HEADER,
                description=_(
                    "Geeft een specifieke API-versie aan in de context van "
                    "een specifieke aanroep. Voorbeeld: 1.2.1."
                ),
                response=True,
            )
        ]

    def get_content_type_headers(self) -> List[OpenApiParameter]:
        if self.method not in ["POST", "PUT", "PATCH"]:
            return []

        return [
            OpenApiParameter(
                name="Content-Type",
                type=str,
                location=OpenApiParameter.HEADER,
                description=_("Content type of the request body."),
                enum=["application/json"],
                required=True,
            )
        ]

    def get_cache_headers(self) -> List[OpenApiParameter]:
        """
        support ETag headers
        """
        if not has_cache_header(self.view):
            return []

        return [
            OpenApiParameter(
                name="If-None-Match",
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description=_(
                    "Perform conditional requests. This header should contain one or "
                    "multiple ETag values of resources the client has cached. If the "
                    "current resource ETag value is in this set, then an HTTP 304 "
                    "empty body will be returned. See "
                    "[MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match) "
                    "for details."
                ),
                examples=[
                    OpenApiExample(
                        name="oneValue",
                        summary=_("One ETag value"),
                        value='"79054025255fb1a26e4bc422aef54eb4"',
                    ),
                    OpenApiExample(
                        name="multipleValues",
                        summary=_("Multiple ETag values"),
                        value='"79054025255fb1a26e4bc422aef54eb4", "e4d909c290d0fb1ca068ffaddf22cbd0"',
                    ),
                ],
            ),
            OpenApiParameter(
                name="ETag",
                type=str,
                location=OpenApiParameter.HEADER,
                response=[200],
                description=_(
                    "De ETag berekend op de response body JSON. "
                    "Indien twee resources exact dezelfde ETag hebben, dan zijn "
                    "deze resources identiek aan elkaar. Je kan de ETag gebruiken "
                    "om caching te implementeren."
                ),
            ),
        ]

    def get_log_headers(self) -> List[OpenApiParameter]:
        if not _view_supports_audittrail(self.view):
            return []

        return [
            OpenApiParameter(
                name=HEADER_LOGRECORD_ID,
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description=_(
                    "Identifier of the request, traceable throughout the network"
                ),
            ),
            OpenApiParameter(
                name=HEADER_AUDIT,
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description=_("Explanation why the request is done"),
            ),
        ]

    def get_location_headers(self) -> List[OpenApiParameter]:
        return [
            OpenApiParameter(
                name="Location",
                type=OpenApiTypes.URI,
                location=OpenApiParameter.HEADER,
                description=_("URL waar de resource leeft."),
                response=[201],
            ),
        ]

    def get_geo_headers(self) -> List[OpenApiParameter]:
        if not isinstance(self.view, GeoMixin):
            return []

        request_headers = []
        if self.method != "DELETE":
            request_headers.append(
                OpenApiParameter(
                    name=HEADER_ACCEPT,
                    type=str,
                    location=OpenApiParameter.HEADER,
                    required=False,
                    description=_(
                        "The desired 'Coordinate Reference System' (CRS) of the response data. "
                        "According to the GeoJSON spec, WGS84 is the default (EPSG: 4326 "
                        "is the same as WGS84)."
                    ),
                    enum=[DEFAULT_CRS],
                )
            )

        if self.method in ("POST", "PUT", "PATCH"):
            request_headers.append(
                OpenApiParameter(
                    name=HEADER_CONTENT,
                    type=str,
                    location=OpenApiParameter.HEADER,
                    required=True,
                    description=_(
                        "The 'Coordinate Reference System' (CRS) of the request data. "
                        "According to the GeoJSON spec, WGS84 is the default (EPSG: 4326 "
                        "is the same as WGS84)."
                    ),
                    enum=[DEFAULT_CRS],
                ),
            )

        response_headers = [
            OpenApiParameter(
                name=HEADER_CONTENT,
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description=_(
                    "The 'Coordinate Reference System' (CRS) of the request data. "
                    "According to the GeoJSON spec, WGS84 is the default (EPSG: 4326 "
                    "is the same as WGS84)."
                ),
                enum=[DEFAULT_CRS],
                response=[200, 201],
            )
        ]

        return request_headers + response_headers

    def get_summary(self):
        if self.method == "HEAD":
            return _("De headers voor een specifiek(e) %(model)s opvragen ") % {
                "model": self.view.queryset.model._meta.verbose_name.upper()
            }
        return super().get_summary()

    def get_description(self):
        if self.method == "HEAD":
            return _("Vraag de headers op die je bij een GET request zou krijgen.")
        return super().get_description()

    def get_filter_backends(self):
        """support expand for detail views"""
        include_allowed = getattr(self.view, "include_allowed", lambda: False)()
        if self.method == "GET" and include_allowed:
            return getattr(self.view, "filter_backends", [])

        return super().get_filter_backends()
