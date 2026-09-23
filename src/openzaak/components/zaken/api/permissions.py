# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from rest_framework.request import Request
from vng_api_common.permissions import bypass_permissions, get_required_scopes

from openzaak.utils.permissions import (
    AuthComponentTypeScopesRequired,
    AuthRequired,
    MultipleObjectsAuthRequired,
)


class ZaakAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at zaaktype and vertrouwelijkheidaanduiding
    of current zaak and check that they are present in the AC for this client
    """

    permission_fields = ("zaaktype", "vertrouwelijkheidaanduiding")
    main_resource = "openzaak.components.zaken.api.viewsets.ZaakViewSet"


class ZaakNestedAuthRequired(ZaakAuthRequired):
    def has_permission(self, request: Request, view) -> bool:
        if bypass_permissions(request):
            return True

        scopes_required = get_required_scopes(request, view)
        component = self.get_component(view)

        main_object = view._get_zaak()
        main_object_data = self.format_data(
            main_object, request, self.get_main_resource(self.main_resource)
        )

        fields = self.get_fields(main_object_data, self.permission_fields)
        return request.jwt_auth.has_auth(scopes_required, component, **fields)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        # all checks are made in has_permission stage
        return True


class ZaakActionAuthRequired(MultipleObjectsAuthRequired):
    permission_fields = {
        "zaak": ZaakAuthRequired.permission_fields,
    }
    main_resources = {
        "zaak": ZaakAuthRequired.main_resource,
    }


class ZaakInzageAuthRequired(ZaakAuthRequired, AuthComponentTypeScopesRequired):
    """Require zaak, besluit and catalogi access for the included resources."""

    def has_permission(self, request: Request, view) -> bool:
        self.has_handler(request, view)

        if bypass_permissions(request):
            return True

        return AuthComponentTypeScopesRequired.has_permission(self, request, view)

    def get_component_permission_fields(self, request, view, component) -> list[dict]:
        resource_config = view.component_permission_resources.get(component)
        if resource_config is None:
            return super().get_component_permission_fields(request, view, component)

        relation, permission_class = resource_config
        zaak = view._get_zaak()
        objects = getattr(zaak, relation).all() if relation else [zaak]
        permission = permission_class()
        resource = permission.get_main_resource(permission.main_resource)
        return [
            permission.get_fields(
                permission.format_data(obj, request, resource),
                permission.permission_fields,
            )
            for obj in objects
        ]

    def has_object_permission(self, request: Request, view, obj) -> bool:
        # all checks are made in has_permission stage
        return True
