# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from rest_framework.request import Request
from vng_api_common.permissions import bypass_permissions

from openzaak.import_data.models import ImportTypeChoices
from openzaak.utils.decorators import convert_cmis_adapter_exceptions
from openzaak.utils.permissions import AuthRequired


class ImportAuthRequired(AuthRequired):
    def get_component(self, view) -> str:
        importer_type = view.import_type
        return ImportTypeChoices.get_component_from_choice(importer_type)

    @convert_cmis_adapter_exceptions
    def has_permission(self, request: Request, view) -> bool:
        has_handler = hasattr(view, request.method.lower())
        if not has_handler:
            view.http_method_not_allowed(request)

        # JWTs are only valid for a short amount of time
        self.check_jwt_expiry(request.jwt_auth.payload)

        if bypass_permissions(request):
            return True

        return request.jwt_auth.has_alle_autorisaties

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if bypass_permissions(request):
            return True

        return request.jwt_auth.has_alle_autorisaties
