from openzaak.utils.permissions import AuthRequired

from django.conf import settings


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
        if settings.CMIS_ENABLED:
            return obj.get_informatieobject()
        else:
            return getattr(obj, permission_main_object).latest_version
