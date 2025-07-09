# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Sequence
from urllib.parse import urlparse

from django.core.exceptions import (
    ImproperlyConfigured,
    ValidationError as DjangoValidationError,
)
from django.db.models import ObjectDoesNotExist
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

import structlog
from rest_framework import exceptions, permissions
from rest_framework.request import Request
from rest_framework.serializers import ValidationError, as_serializer_error
from rest_framework.viewsets import ViewSetMixin
from vng_api_common.permissions import bypass_permissions, get_required_scopes
from vng_api_common.utils import get_resource_for_path

from openzaak.utils.decorators import convert_cmis_adapter_exceptions

logger = structlog.stdlib.get_logger(__name__)


class AuthRequired(permissions.BasePermission):
    """
    Look at the scopes required for the current action
    and check that they are present in the AC for this client
    """

    permission_fields = ()
    main_resource = None

    def get_component(self, view) -> str:
        return view.queryset.model._meta.app_label

    def get_fields(self, data, permission_fields):
        if not isinstance(data, dict):
            raise exceptions.ParseError()
        return {field: data.get(field) for field in permission_fields}

    def format_data(self, obj, request, main_resource) -> dict:
        serializer_class = main_resource.serializer_class
        serializer = serializer_class(obj, context={"request": request})
        return serializer.data

    def get_main_resource(self, main_resource):
        if not main_resource:
            raise ImproperlyConfigured(
                "'%s' should either include a `main_resource` "
                "attribute, or override the `get_main_resource()` method."
                % self.__class__.__name__
            )
        return import_string(main_resource)

    def get_main_object(self, obj, permission_main_object):
        return getattr(obj, permission_main_object)

    def has_handler(self, request, view):
        if not hasattr(view, request.method.lower()):
            view.http_method_not_allowed(request)

    def validate_create(
        self,
        request,
        view,
        main_object_data,
        permission_fields,
        main_resource,
        serializer_class,
    ):
        if view.__class__ is main_resource:
            fields = self.get_fields(main_object_data, permission_fields)
            # validate fields, since it's a user input
            non_empty_fields = {name: value for name, value in fields.items() if value}
            if non_empty_fields:
                serializer = serializer_class(
                    data=non_empty_fields,
                    partial=True,
                    context={"request": request},
                )
                serializer.is_valid(raise_exception=True)

        else:
            try:
                main_object_url = main_object_data[view.permission_main_object]
                main_object_path = urlparse(main_object_url).path
                main_object = get_resource_for_path(main_object_path)
            except KeyError:
                raise ValidationError(
                    {
                        view.permission_main_object: _(
                            "{} is required for permissions"
                        ).format(view.permission_main_object),
                    },
                    code="required",
                )
            except ObjectDoesNotExist:
                raise ValidationError(
                    {
                        view.permission_main_object: ValidationError(
                            _("The object does not exist in the database"),
                            code="object-does-not-exist",
                        ).detail
                    }
                )
            except DjangoValidationError as exc:
                err_dict = as_serializer_error(
                    ValidationError({view.permission_main_object: exc})
                )
                raise ValidationError(err_dict)

            main_object_data = self.format_data(main_object, request, main_resource)
            fields = self.get_fields(main_object_data, permission_fields)

        return fields

    @convert_cmis_adapter_exceptions
    def has_permission(self, request: Request, view) -> bool:
        # permission checks run before the handler is determined. if there is no handler,
        # a "method is not allowed" must be raised, not an HTTP 403 (see #385)
        # this implementation works for both APIView and viewsets
        self.has_handler(request, view)

        if bypass_permissions(request):
            return True

        scopes_required = get_required_scopes(request, view)
        component = self.get_component(view)

        if not self.permission_fields:
            return request.jwt_auth.has_auth(scopes_required, component)

        if view.action == "create":
            fields = self.validate_create(
                request,
                view,
                request.data,
                self.permission_fields,
                self.get_main_resource(self.main_resource),
                view.get_serializer_class(),
            )
            return request.jwt_auth.has_auth(scopes_required, component, **fields)

        # detect if this is an unsupported method - if it's a viewset and the
        # action was not mapped, it's not supported and DRF will catch it
        if view.action is None and isinstance(view, ViewSetMixin):
            return True

        # by default - check if the action is allowed at all
        return request.jwt_auth.has_auth(scopes_required, component)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if bypass_permissions(request):
            return True

        scopes_required = get_required_scopes(request, view)
        component = self.get_component(view)

        if not self.permission_fields:
            return request.jwt_auth.has_auth(scopes_required, component)

        main_resource = self.get_main_resource(self.main_resource)

        if view.__class__ is main_resource:
            main_object = obj
        else:
            main_object = self.get_main_object(obj, view.permission_main_object)

        main_object_data = self.format_data(main_object, request, main_resource)
        fields = self.get_fields(main_object_data, self.permission_fields)
        return request.jwt_auth.has_auth(scopes_required, component, **fields)


class MultipleObjectsAuthRequired(AuthRequired):
    permission_fields: dict[str, Sequence[str]]
    main_resources: dict

    def get_field_viewset(self, viewset, action):
        field_viewset = import_string(viewset)()
        field_viewset.action = action

        return field_viewset

    @convert_cmis_adapter_exceptions
    def has_permission(self, request, view):
        self.has_handler(request, view)

        if bypass_permissions(request):
            return True

        if view.action is None and isinstance(view, ViewSetMixin):
            return True

        if not getattr(view, "viewset_classes", None):
            return False  # TODO could raise ImproperlyConfigured, permission_main_object can also be forgotten on viewset

        for field, viewset in view.viewset_classes.items():
            # CatalogusAutorisatie (_autorisaties) is cached in JWTAuth
            if hasattr(request.jwt_auth, "_autorisaties"):
                del request.jwt_auth._autorisaties

            fieldset_view = self.get_field_viewset(viewset, view.action)

            scopes_required = get_required_scopes(request, fieldset_view)
            component = self.get_component(fieldset_view)
            fields = []

            if self.permission_fields and view.action == "create":
                fields = self.validate_create(
                    request,
                    fieldset_view,
                    request.data.get(field, {}),
                    self.permission_fields.get(field),
                    self.get_main_resource(self.main_resources.get(field)),
                    fieldset_view.get_serializer_class(),
                )

            if not request.jwt_auth.has_auth(scopes_required, component, **fields):
                return False

        return True  # all field viewsets where valid

    def has_object_permission(self, request: Request, view, obj) -> bool:
        raise NotImplementedError()
