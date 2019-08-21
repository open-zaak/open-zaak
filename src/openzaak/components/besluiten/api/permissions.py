from vng_api_common.permissions import (
    BaseAuthRequired,
    MainObjAuthScopesRequired,
    RelatedObjAuthScopesRequired,
)
from openzaak.utils.permissions import AuthComponentMixin


class BesluitAuthScopesRequired(AuthComponentMixin, MainObjAuthScopesRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of current informatieobject and check that they are present in the AC for this client
    """

    permission_fields = ("besluittype",)


class BesluitBaseAuthRequired(AuthComponentMixin, BaseAuthRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of related informatieobject and check that they are present in the AC for this client
    """

    permission_fields = ("besluittype",)
    obj_path = "besluit"



class BesluitRelatedAuthScopesRequired(AuthComponentMixin, RelatedObjAuthScopesRequired):
    """
    Look at the scopes required for the current action and at besluittype
    of related besluit and check that they are present in the AC for this client
    """

    permission_fields = ("besluittype",)
    obj_path = "besluit"
