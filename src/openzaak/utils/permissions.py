# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import time
from typing import Any, Dict
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import (
    ImproperlyConfigured,
    ValidationError as DjangoValidationError,
)
from django.db.models import ObjectDoesNotExist
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.serializers import ValidationError, as_serializer_error
from vng_api_common.permissions import bypass_permissions, get_required_scopes
from vng_api_common.utils import get_resource_for_path


class AuthRequired(permissions.BasePermission):
    """
    Look at the scopes required for the current action
    and check that they are present in the AC for this client
    """

    permission_fields = ()
    main_resource = None

    def get_component(self, view) -> str:
        return view.queryset.model._meta.app_label

    def get_fields(self, data):
        return {field: data.get(field) for field in self.permission_fields}

    def format_data(self, obj, request) -> dict:
        main_resource = self.get_main_resource()
        serializer_class = main_resource.serializer_class
        serializer = serializer_class(obj, context={"request": request})
        return serializer.data

    def get_main_resource(self):
        if not self.main_resource:
            raise ImproperlyConfigured(
                "'%s' should either include a `main_resource` "
                "attribute, or override the `get_main_resource()` method."
                % self.__class__.__name__
            )
        return import_string(self.main_resource)

    def get_main_object(self, obj, permission_main_object):
        return getattr(obj, permission_main_object)

    def check_jwt_expiry(self, payload: Dict[str, Any]) -> None:
        """
        Verify that the token was issued recently enough.

        The Django settings define how long a JWT is considered to be valid. Adding
        that duration to the issued-at claim determines the upper limit for token
        validity.
        """
        if not payload:
            return

        iat = payload.get("iat")
        if iat is None:
            raise PermissionDenied(
                _("The JWT is mising the 'iat' claim."), code="jwt-missing-iat-claim"
            )

        current_timestamp = time.time()
        if current_timestamp - iat >= settings.JWT_EXPIRY:
            raise PermissionDenied(
                _("The JWT used for this request is expired"), code="jwt-expired"
            )

    def has_permission(self, request: Request, view) -> bool:
        # permission checks run before the handler is determined. if there is no handler,
        # a "method is not allowed" must be raised, not an HTTP 403 (see #385)
        # this implementation works for both APIView and viewsets
        has_handler = hasattr(view, request.method.lower())
        if not has_handler:
            view.http_method_not_allowed(request)

        # JWTs are only valid for a short amount of time
        self.check_jwt_expiry(request.jwt_auth.payload)

        from rest_framework.viewsets import ViewSetMixin

        if bypass_permissions(request):
            return True

        scopes_required = get_required_scopes(view)
        component = self.get_component(view)

        if not self.permission_fields:
            return request.jwt_auth.has_auth(scopes_required, component)

        main_resource = self.get_main_resource()

        if view.action == "create":
            if view.__class__ is main_resource:
                main_object_data = request.data

            else:
                main_object_url = request.data[view.permission_main_object]
                main_object_path = urlparse(main_object_url).path
                try:
                    main_object = get_resource_for_path(main_object_path)
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

                main_object_data = self.format_data(main_object, request)

            fields = self.get_fields(main_object_data)
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

        scopes_required = get_required_scopes(view)
        component = self.get_component(view)

        if not self.permission_fields:
            return request.jwt_auth.has_auth(scopes_required, component)

        main_resource = self.get_main_resource()

        if view.__class__ is main_resource:
            main_object = obj
        else:
            main_object = self.get_main_object(obj, view.permission_main_object)

        main_object_data = self.format_data(main_object, request)
        fields = self.get_fields(main_object_data)
        return request.jwt_auth.has_auth(scopes_required, component, **fields)
