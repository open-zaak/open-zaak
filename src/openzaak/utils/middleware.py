import logging

from vng_api_common.middleware import AuthMiddleware as _AuthMiddleware, JWTAuth as _JWTAuth
from vng_api_common.authorizations.models import Autorisatie, Applicatie
from django.http import HttpRequest
from django.db import models
from django.db.models import Subquery
from typing import List, Union
from vng_api_common.constants import ComponentTypes

logger = logging.getLogger(__name__)

COMPONENT_MAPPING = {
    'authorizations': ComponentTypes.ac,
    'zaken': ComponentTypes.zrc,
    'catalogi': ComponentTypes.ztc,
    'documenten': ComponentTypes.drc,
    'besluiten': ComponentTypes.brc
}


class LogHeadersMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        self.log(request)
        return self.get_response(request) if self.get_response else None

    def log(self, request: HttpRequest):
        logger.debug("Request headers for %s: %r", request.path, request.headers)


class JWTAuth(_JWTAuth):
    def __init__(self, encoded: str = None):
        self.encoded = encoded
        self.component = None

    def set_component(self, component):
        self.component = COMPONENT_MAPPING.get(component, component)

    @property
    def applicaties(self) -> Union[list, None]:
        if self.client_id is None:
            return []

        return Applicatie.objects.filter(client_ids__contains=[self.client_id])

    @property
    def autorisaties(self) -> models.QuerySet:
        """
        Retrieve all authorizations relevant to this component.
        """
        app_ids = self.applicaties.values('id')
        return Autorisatie.objects.filter(
                applicatie_id__in=Subquery(app_ids),
                component=self.component
            )

    def has_auth(self, scopes: List[str], **fields) -> bool:
        if scopes is None:
            return False

        scopes_provided = set()

        # allow everything
        if self.applicaties.filter(heeft_alle_autorisaties=True).exists():
            return True

        if not self.component:
            return False

        autorisaties = self.autorisaties

        # filter on all additional components
        for field_name, field_value in fields.items():
            if hasattr(self, f'filter_{field_name}'):
                autorisaties = getattr(self, f'filter_{field_name}')(autorisaties, field_value)
            else:
                autorisaties = self.filter_default(autorisaties, field_name, field_value)

        for autorisatie in autorisaties:
            scopes_provided.update(autorisatie.scopes)

        return scopes.is_contained_in(list(scopes_provided))


class AuthMiddleware(_AuthMiddleware):
    def extract_jwt_payload(self, request):
        authorization = request.META.get(self.header, '')
        prefix = f"{self.auth_type} "
        if authorization.startswith(prefix):
            # grab the actual token
            encoded = authorization[len(prefix):]
        else:
            encoded = None

        request.jwt_auth = JWTAuth(encoded)
