# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Q, Value, When
from django.http.request import validate_host

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resources_for_paths


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

    @property
    def prefix(self):
        return (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )

    def build_queryset(self, local_filters, external_filters) -> models.QuerySet:
        if not self.vertrouwelijkheidaanduiding_use:
            del local_filters["_va_order__lte"]
            del external_filters["_va_order__lte"]

        _local_filters = Q()
        for k, v in local_filters.items():
            _local_filters &= Q(**{k: v})

        _external_filters = Q()
        for k, v in external_filters.items():
            _external_filters &= Q(**{k: v})

        if self.vertrouwelijkheidaanduiding_use:
            # annotate the queryset so we can map a string value to a logical number
            order_case = VertrouwelijkheidsAanduiding.get_order_expression(
                f"{self.prefix}vertrouwelijkheidaanduiding"
            )
            annotations = {"_va_order": order_case}
            # bring it all together now to build the resulting queryset
            queryset = self.annotate(**annotations).filter(
                _local_filters | _external_filters
            )

        else:
            queryset = self.filter(_local_filters | _external_filters)
        return queryset

    def get_filters(
        self, scope, authorizations, catalogus_authorizations=None, local=True
    ) -> dict:
        prefix = self.prefix
        loose_fk_field = (
            f"_{self.loose_fk_field}" if local else f"_{self.loose_fk_field}_url"
        )

        # resource URLs to either use as-is or resolve to database records
        resource_urls = [
            getattr(authorization, self.loose_fk_field)
            for authorization in authorizations
        ]

        # keep a list of allowed loose-fk objects
        loose_fk_objecten = []
        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        vertrouwelijkheidaanduiding_whens = []

        if not local:
            loose_fk_object_map = dict(zip(resource_urls, resource_urls))
        else:
            # prepare to get the loose_fk_objects in bulk from the DB
            loose_fk_object_paths = [urlparse(url).path for url in resource_urls]
            loose_fk_objects = get_resources_for_paths(loose_fk_object_paths)
            # nothing to resolve
            if loose_fk_objects is None:
                loose_fk_object_map = {}
            else:
                # keep the sorting so we can zip them correctly
                sorted_objects = sorted(
                    loose_fk_objects, key=lambda o: o.get_absolute_api_url()
                )
                loose_fk_object_map = dict(zip(sorted(resource_urls), sorted_objects))

        for authorization in authorizations:
            resource_url = getattr(authorization, self.loose_fk_field)
            loose_fk_object = loose_fk_object_map[resource_url]
            loose_fk_objecten.append(loose_fk_object)

            # extract the order and map it to the database value
            if authorization.max_vertrouwelijkheidaanduiding:
                choice_item_order = VertrouwelijkheidsAanduiding.get_choice_order(
                    authorization.max_vertrouwelijkheidaanduiding
                )
                vertrouwelijkheidaanduiding_whens.append(
                    When(
                        **{f"{prefix}{loose_fk_field}": loose_fk_object},
                        then=Value(choice_item_order),
                    )
                )

        if catalogus_authorizations:
            for catalogus_authorisation in catalogus_authorizations:
                resources = getattr(
                    catalogus_authorisation.catalogus, f"{self.loose_fk_field}_set"
                ).all()

                for instance in resources:
                    loose_fk_objecten.append(instance)

                    # extract the order and map it to the database value
                    if catalogus_authorisation.max_vertrouwelijkheidaanduiding:
                        choice_item_order = (
                            VertrouwelijkheidsAanduiding.get_choice_order(
                                catalogus_authorisation.max_vertrouwelijkheidaanduiding
                            )
                        )
                        vertrouwelijkheidaanduiding_whens.append(
                            When(
                                **{f"{prefix}{loose_fk_field}": instance},
                                then=Value(choice_item_order),
                            )
                        )

        # filtering:
        # * only allow the white-listed loose-fk objects, explicitly
        # * apply the filtering to limit cases within case-types to the maximal
        #   confidentiality level
        filters = {
            f"{prefix}{loose_fk_field}__in": loose_fk_objecten,
            "_va_order__lte": Case(
                *vertrouwelijkheidaanduiding_whens, output_field=IntegerField()
            ),
        }
        return filters

    def get_authorizations(self, scope: Scope, authorizations: models.QuerySet):
        authorizations_local = []
        authorizations_external = []
        allowed_hosts = settings.ALLOWED_HOSTS

        for auth in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(auth.scopes):
                continue

            loose_fk_host = urlparse(getattr(auth, self.loose_fk_field)).hostname
            if validate_host(loose_fk_host, allowed_hosts):
                authorizations_local.append(auth)
            else:
                authorizations_external.append(auth)

        return authorizations_local, authorizations_external

    def filter_for_authorizations(
        self,
        scope: Scope,
        authorizations: models.QuerySet,
        catalogus_authorizations: models.QuerySet,
    ) -> models.QuerySet:

        # todo implement error if no loose-fk field

        authorizations_local, authorizations_external = self.get_authorizations(
            scope, authorizations
        )

        local_filters = self.get_filters(
            scope,
            authorizations_local,
            catalogus_authorizations=catalogus_authorizations,
            local=True,
        )
        external_filters = self.get_filters(scope, authorizations_external, local=False)
        return self.build_queryset(local_filters, external_filters)
