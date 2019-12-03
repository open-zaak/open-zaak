from urllib.parse import urlparse

from typing import Union
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.conf import settings

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resource_for_path

from openzaak.utils.query import BlockChangeMixin


class AuthorizationsFilterMixin:
    authorizations_lookup = None

    def get_zaaktype(self, authorization, local=True) -> Union[models.Model, str]:
        if local:
            zaaktype_path = urlparse(authorization.zaaktype).path
            zaaktype = get_resource_for_path(zaaktype_path)
        else:
            zaaktype = authorization.zaaktype
        return zaaktype

    def filter_by_auth_query(self, scope, authorizations, local=True) -> models.QuerySet:
        prefix = (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )
        zaaktype_field = "zaaktype" if local else "_zaaktype_url"

        # annotate the queryset so we can map a string value to a logical number
        order_case = VertrouwelijkheidsAanduiding.get_order_expression(
            f"{prefix}vertrouwelijkheidaanduiding"
        )

        # keep a list of allowed zaaktypen
        zaaktypen = []
        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        vertrouwelijkheidaanduiding_whens = []

        for authorization in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(authorization.scopes):
                continue

            zaaktype = self.get_zaaktype(authorization, local)
            zaaktypen.append(zaaktype)

            # extract the order and map it to the database value
            choice_item = VertrouwelijkheidsAanduiding.get_choice(
                authorization.max_vertrouwelijkheidaanduiding
            )
            vertrouwelijkheidaanduiding_whens.append(
                When(**{f"{prefix}{zaaktype_field}": zaaktype}, then=Value(choice_item.order))
            )

        # apply the order annnotation so we can filter later
        annotations = {f"{prefix}_va_order": order_case}
        # filtering:
        # * only allow the white-listed zaaktypen, explicitly
        # * apply the filtering to limit cases within case-types to the maximal
        #   confidentiality level
        filters = {
            f"{prefix}{zaaktype_field}__in": zaaktypen,
            f"{prefix}_va_order__lte": Case(
                *vertrouwelijkheidaanduiding_whens, output_field=IntegerField()
            ),
        }

        # bring it all together now to build the resulting queryset
        queryset = self.annotate(**annotations).filter(**filters)
        return queryset

    def filter_for_authorizations(
        self, scope: Scope, authorizations: models.QuerySet
    ) -> models.QuerySet:
        """
        Filter objects whitelisted by the authorizations.

        For ZRC, authorizations are defined around ``Autorisatie.zaaktype``,
        with a ``max_vertrouwelijkheidaanduiding`` limiting the confidentiality
        level of ``zaken`` (inclusive), and scopes that apply for the
        ``zaaktype`` at hand.

        This means that ``zaken`` are included if, and only if:

        * the ``zaaktype`` is provided in ``authorizations``
        * the scopes for the ``zaaktype`` in each ``authorization`` contain the
          required``scope``
        * the ``zaak.vertrouwelijkheidaanduiding`` is less then or equal to the
          ``authorization.max_vertrouwelijkheidaanduiding``

        :param scope: a (possibly complex) scope that must be granted on the
          authorizations
        :param authorizations: queryset of
          :class:`vng_api_common.authorizations.Autorisatie` objects

        :return: a queryset of filtered results according to the
          authorizations provided
        """
        authorizations_local = []
        authorizarions_external = []
        for auth in authorizations:
            zaaktype_host = urlparse(auth.zaaktype).hostname
            if zaaktype_host in settings.ALLOWED_HOSTS:
                authorizations_local.append(auth)
            else:
                authorizarions_external.append(auth)

        queryset_local = self.filter_by_auth_query(scope, authorizations_local, local=True)
        queryset_external = self.filter_by_auth_query(scope, authorizarions_external, local=False)

        return queryset_local.union(queryset_external)


class ZaakQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    pass


class ZaakRelatedQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "zaak"


class ZaakInformatieObjectQuerySet(BlockChangeMixin, ZaakRelatedQuerySet):
    pass
