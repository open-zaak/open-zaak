from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.db.models import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from rest_framework.serializers import ValidationError
from rest_framework import permissions
from rest_framework.request import Request
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

    def has_permission(self, request: Request, view) -> bool:
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
                    raise ValidationError({
                        view.permission_main_object: ValidationError(
                            _('The object does not exist in the database'),
                            code='object-does-not-exist'
                        ).detail
                    })
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
