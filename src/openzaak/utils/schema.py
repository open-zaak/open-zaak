import logging

from django.conf import settings

from vng_api_common.inspectors.view import AutoSchema as _AutoSchema
from vng_api_common.permissions import get_required_scopes

from .permissions import AuthRequired

logger = logging.getLogger(__name__)


class AutoSchema(_AutoSchema):
    def get_security(self):
        """Return a list of security requirements for this operation.

        Returning an empty list marks the endpoint as unauthenticated (i.e. removes all accepted
        authentication schemes). Returning ``None`` will inherit the top-level secuirty requirements.

        :return: security requirements
        :rtype: list[dict[str,list[str]]]"""
        permissions = self.view.get_permissions()
        scope_permissions = [
            perm for perm in permissions if isinstance(perm, AuthRequired)
        ]

        if not scope_permissions:
            return super().get_security()

        if len(permissions) != len(scope_permissions):
            logger.warning(
                "Can't represent all permissions in OAS for path %s and method %s",
                self.path,
                self.method,
            )

        required_scopes = []
        for perm in scope_permissions:
            scopes = get_required_scopes(self.view)
            if scopes is None:
                continue
            required_scopes.append(scopes)

        if not required_scopes:
            return None  # use global security

        scopes = [str(scope) for scope in sorted(required_scopes)]

        # operation level security
        return [{settings.SECURITY_DEFINITION_NAME: scopes}]
