# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.permissions import bypass_permissions, get_required_scopes

from openzaak.components.zaken.api.permissions import ZaakAuthRequired
from openzaak.utils.permissions import AuthRequired, MultipleObjectsAuthRequired


class InformationObjectAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of current informatieobject and check that they are present in the AC for this client
    """

    permission_fields = ("informatieobjecttype", "vertrouwelijkheidaanduiding")
    main_resource = (
        "openzaak.components.documenten.api.viewsets.EnkelvoudigInformatieObjectViewSet"
    )

    def get_main_object(self, obj, permission_main_object):
        return obj.get_informatieobject(permission_main_object)

    def has_object_permission(self, request, view, obj):
        if not super().has_object_permission(request, view, obj):
            return False

        # Autorisaties API 1.1.0 introduced `alleen_is_gereed_voor_publicatie`
        # When enabled, only include documents with `is_gereed_voor_publicatie=True`
        has_alleen_is_gereed_voor_publicatie = not any(
            app.alleen_is_gereed_voor_publicatie for app in request.jwt_auth.applicaties
        )
        if bypass_permissions(request):
            # Add additional check for alleen_is_gereed_voor_publicatie
            if has_alleen_is_gereed_voor_publicatie:
                pass
            return True

        if has_alleen_is_gereed_voor_publicatie:
            return True

        document = (
            obj
            if view.__class__ is self.get_main_resource(self.main_resource)
            else self.get_main_object(obj, view.permission_main_object)
        )

        # Check if scopes_required are available and if the document `is_gereed_voor_publicatie`=True
        scopes_required = get_required_scopes(request, view)
        component = self.get_component(view)
        return (
            request.jwt_auth.has_auth(scopes_required, component=component)
            and document.is_gereed_voor_publicatie
        )


class DocumentRegistrerenAuthRequired(MultipleObjectsAuthRequired):
    permission_fields = {
        "enkelvoudiginformatieobject": InformationObjectAuthRequired.permission_fields,
        "zaakinformatieobject": ZaakAuthRequired.permission_fields,
    }
    main_resources = {
        "enkelvoudiginformatieobject": InformationObjectAuthRequired.main_resource,
        "zaakinformatieobject": ZaakAuthRequired.main_resource,
    }
