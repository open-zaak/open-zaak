# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.request import Request
from vng_api_common.permissions import bypass_permissions, get_required_scopes

from openzaak.utils.permissions import AuthRequired


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

        scopes_required = get_required_scopes(view)
        component = self.get_component(view)

        main_object = view._get_zaak()
        main_object_data = self.format_data(main_object, request)

        fields = self.get_fields(main_object_data)
        return request.jwt_auth.has_auth(scopes_required, component, **fields)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        # all checks are made in has_permission stage
        return True
