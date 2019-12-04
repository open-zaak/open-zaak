from typing import Union
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.http.request import validate_host

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resource_for_path


class QueryBlocked(Exception):
    pass


class BlockChangeMixin:
    def _block(self, method: str):
        raise QueryBlocked(
            f"Queryset/manager `{method}` is forbidden for {self.model.__name__}. "
            "These methods do not fire signals, which are relied upon."
        )

    def bulk_create(self, *args, **kwargs):
        self._block("bulk_create")

    def bulk_update(self, *args, **kwargs):
        self._block("bulk_update")

    def update(self, *args, **kwargs):
        self._block("update")

    def delete(self, *args, **kwargs):
        self._block("delete")

    # see django.db.models.query.QuerySet.delete
    delete.queryset_only = True


class LooseFkAuthorizationsFilterMixin:
    auth_fields = []
    loose_fk_field = None
    vertrouwelijkheidaanduiding_use = True
    authorizations_lookup = None

    def get_loose_fk_object(
        self, authorization, local=True
    ) -> Union[models.Model, str]:
        if local:
            zaaktype_path = urlparse(authorization.zaaktype).path
            zaaktype = get_resource_for_path(zaaktype_path)
        else:
            zaaktype = authorization.zaaktype
        return zaaktype

    def filter_by_auth_query(
        self, scope, authorizations, local=True
    ) -> models.QuerySet:
        prefix = (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )
        loose_fk_field = self.loose_fk_field if local else f"_{self.loose_fk_field}_url"

        # keep a list of allowed loose-fk objects
        loose_fk_objecten = []
        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        vertrouwelijkheidaanduiding_whens = []

        for authorization in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(authorization.scopes):
                continue

            loose_fk_object = self.get_loose_fk_object(authorization, local)
            loose_fk_objecten.append(loose_fk_object)

            # extract the order and map it to the database value
            choice_item = VertrouwelijkheidsAanduiding.get_choice(
                authorization.max_vertrouwelijkheidaanduiding
            )
            vertrouwelijkheidaanduiding_whens.append(
                When(
                    **{f"{prefix}{loose_fk_field}": loose_fk_object},
                    then=Value(choice_item.order),
                )
            )

        # filtering:
        # * only allow the white-listed loose-fk objects, explicitly
        # * apply the filtering to limit cases within case-types to the maximal
        #   confidentiality level
        filters = {f"{prefix}{loose_fk_field}__in": loose_fk_objecten}

        if self.vertrouwelijkheidaanduiding_use:
            # annotate the queryset so we can map a string value to a logical number
            order_case = VertrouwelijkheidsAanduiding.get_order_expression(
                f"{prefix}vertrouwelijkheidaanduiding"
            )
            annotations = {f"{prefix}_va_order": order_case}
            filters[f"{prefix}_va_order__lte"] = Case(
                *vertrouwelijkheidaanduiding_whens, output_field=IntegerField()
            )
            # bring it all together now to build the resulting queryset
            queryset = self.annotate(**annotations).filter(**filters)

        else:
            queryset = self.filter(**filters)

        return queryset

    def filter_for_authorizations(
        self, scope: Scope, authorizations: models.QuerySet
    ) -> models.QuerySet:

        # todo implement error if no loose-fk field

        authorizations_local = []
        authorizarions_external = []

        for auth in authorizations:
            loose_fk_host = urlparse(getattr(auth, self.loose_fk_field)).netloc
            allowed_hosts = settings.ALLOWED_HOSTS

            if validate_host(loose_fk_host, allowed_hosts):
                authorizations_local.append(auth)
            else:
                authorizarions_external.append(auth)

        queryset_local = self.filter_by_auth_query(
            scope, authorizations_local, local=True
        ).values_list("pk", flat=True)
        queryset_external = self.filter_by_auth_query(
            scope, authorizarions_external, local=False
        ).values_list("pk", flat=True)
        queryset = self.filter(pk__in=queryset_local.union(queryset_external))

        return queryset
