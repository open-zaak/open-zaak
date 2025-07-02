# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.zaken.api.permissions import ZaakAuthRequired
from openzaak.components.zaken.api.serializers import ZaakInformatieObjectSerializer
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


class RegisterDocumentAuthRequired(AuthRequired):
    permission_fields = ("zaakinformatieobject",)
    main_resource = "openzaak.components.zaken.api.viewsets.ZaakInformatieObjectViewSet"



class DocumentReserverenAuthRequired(MultipleObjectsAuthRequired):
    permission_fields = {
        "enkelvoudiginformatieobject": InformationObjectAuthRequired.permission_fields,
        "zaakinformatieobject": ZaakAuthRequired.permission_fields,
    }
    main_resources = {
        "enkelvoudiginformatieobject": InformationObjectAuthRequired.main_resource,
        "zaakinformatieobject": ZaakAuthRequired.main_resource,
    }
