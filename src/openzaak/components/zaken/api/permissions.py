# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.db.models import Manager

from rest_framework.request import Request
from vng_api_common.permissions import bypass_permissions, get_required_scopes
from vng_api_common.scopes import Scope

from openzaak.components.besluiten.api.permissions import BesluitAuthRequired
from openzaak.utils.constants import COMPONENT_MAPPING
from openzaak.utils.permissions import (
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


class ZaakInzageMultipleObjectsAuthRequired(MultipleObjectsAuthRequired):
    """
    Check the zaak and all nested resources with their own authorization
    (hoofdzaak, deelzaken and besluiten).
    """

    permission_fields = {
        "zaak": ZaakAuthRequired.permission_fields,
        "hoofdzaak": ZaakAuthRequired.permission_fields,
        "deelzaken": ZaakAuthRequired.permission_fields,
        "besluiten": BesluitAuthRequired.permission_fields,
    }
    main_resources = {
        "zaak": ZaakAuthRequired.main_resource,
        "hoofdzaak": ZaakAuthRequired.main_resource,
        "deelzaken": ZaakAuthRequired.main_resource,
        "besluiten": BesluitAuthRequired.main_resource,
    }
    # Fields without a relation validate the zaak itself.
    object_relations = {
        "hoofdzaak": "hoofdzaak",
        "deelzaken": "deelzaken",
        "besluiten": "besluit_set",
    }

    def get_field_objects(self, obj, field):
        relation = self.object_relations.get(field)
        if relation is None:
            return [obj]
        related = getattr(obj, relation)
        if isinstance(related, Manager):
            return list(related.all())
        return [] if related is None else [related]

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if bypass_permissions(request):
            return True

        if not getattr(view, "viewset_classes", None):
            return False

        # Check if user has all required scopes with its different component types
        main_required_scopes = self.has_component_scopes(
            request, get_required_scopes(request, view)
        )
        if not main_required_scopes:
            return False

        # Check authorization for each resources
        for field, viewset in view.viewset_classes.items():
            fieldset_view = self.get_field_viewset(
                viewset,
                view.action,
            )

            scopes_required = get_required_scopes(request, fieldset_view)

            component = self.get_component(fieldset_view)
            fields = {}

            permission_fields = self.permission_fields.get(field)

            if permission_fields:
                main_resource = self.get_main_resource(self.main_resources.get(field))
                for field_object in self.get_field_objects(obj, field):
                    main_object_data = self.format_data(
                        field_object, request, main_resource
                    )
                    fields = self.get_fields(main_object_data, permission_fields)

                    if not request.jwt_auth.has_auth(
                        scopes_required, component, **fields
                    ):
                        return False
                continue

            if not request.jwt_auth.has_auth(scopes_required, component, **fields):
                return False

        return True

    def get_scope_component_types(self, scope: Scope):
        if not scope.children:
            yield scope, COMPONENT_MAPPING.get(scope.label.partition(".")[0])
            return
        for child in scope.children:
            yield from self.get_scope_component_types(child)

    def has_component_scopes(self, request: Request, scope: Scope | None) -> bool:
        # Get each required scope and its component types and verify that all pairs are authorized
        if scope is None:
            return False
        checks = [
            component is not None
            and request.jwt_auth.has_auth(required_scope, component)
            for required_scope, component in self.get_scope_component_types(scope)
        ]
        return all(checks)
