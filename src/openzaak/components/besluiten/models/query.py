from urllib.parse import urlparse

from django.db import models

from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resource_for_path


class AuthorizationsFilterMixin:
    authorizations_lookup = None

    def filter_for_authorizations(
        self, scope: Scope, authorizations: models.QuerySet
    ) -> models.QuerySet:
        """
        Filter objects whitelisted by the authorizations.

        For BRC, authorizations are defined around ``Autorisatie.besluittype``,
        limiting scopes that apply for the ``besluittype`` at hand.

        This means that ``besluiten`` are included if, and only if:

        * the ``besluittype`` is provided in ``authorizations``
        * the scopes for the ``besluittype`` in each ``authorization`` contain the
          required``scope``

        :param scope: a (possibly complex) scope that must be granted on the
          authorizations
        :param authorizations: queryset of
          :class:`vng_api_common.authorizations.Autorisatie` objects

        :return: a queryset of filtered results according to the
          authorizations provided
        """
        prefix = (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )

        # keep a list of allowed besluittypen
        besluittypen = []
        for authorization in authorizations:
            if scope.is_contained_in(authorization.scopes):
                besluittype_path = urlparse(authorization.besluittype).path
                besluittype = get_resource_for_path(besluittype_path)
                besluittypen.append(besluittype)

        # filtering:
        # * only allow the white-listed besluittypen, explicitly
        queryset = self.filter(**{f"{prefix}besluittype__in": besluittypen})
        return queryset


class BesluitQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    pass


class BesluitRelatedQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "besluit"
