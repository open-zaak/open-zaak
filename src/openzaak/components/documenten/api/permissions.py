from urllib.parse import urlparse

from vng_api_common.permissions import (
    MainObjAuthScopesRequired, RelatedObjAuthScopesRequired
)
from vng_api_common.utils import get_resource_for_path


class InformationObjectAuthScopesRequired(MainObjAuthScopesRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of current informatieobject and check that they are present in the AC for this client
    """
    permission_fields = ('informatieobjecttype', 'vertrouwelijkheidaanduiding')


class InformationObjectRelatedAuthScopesRequired(RelatedObjAuthScopesRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of related informatieobject and check that they are present in the AC for this client
    """
    permission_fields = ('informatieobjecttype', 'vertrouwelijkheidaanduiding')
    obj_path = 'informatieobject.latest_version'

    def _get_obj(self, view, request):
        """
        Overridden to ensure that the correct key is used to retrieve the url
        from the request data
        """
        main_obj_path = request.data.get(self.obj_path.split('.')[0], None)
        main_obj_url = urlparse(main_obj_path).path
        main_obj = get_resource_for_path(main_obj_url)
        return main_obj
