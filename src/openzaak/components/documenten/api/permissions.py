# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.utils.permissions import AuthRequired


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
