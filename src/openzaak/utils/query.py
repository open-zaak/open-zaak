# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import defaultdict

from django.db import models
from django.db.models import Q

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope


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

    def build_queryset(self, filters) -> models.QuerySet:
        if self.vertrouwelijkheidaanduiding_use:
            # annotate the queryset so we can map a string value to a logical number
            order_case = VertrouwelijkheidsAanduiding.get_order_expression(
                f"{self.prefix}vertrouwelijkheidaanduiding"
            )
            annotations = {"_va_order": order_case}
            # bring it all together now to build the resulting queryset
            queryset = self.annotate(**annotations).filter(filters)

        else:
            queryset = self.filter(filters)
        return queryset

    def get_filters(
        self,
        scope,
        authorizations,
        catalogus_authorizations=None,
        use_va=True,
    ) -> Q:
        prefix = self.prefix
        loose_fk_field = f"_{self.loose_fk_field}"

        # # resource URLs to either use as-is or resolve to database records
        # resource_urls = [
        #     getattr(authorization, self.loose_fk_field)
        #     for authorization in authorizations
        # ]

        # keep a list of allowed loose-fk objects
        loose_fk_objecten = []
        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        va_mapping = defaultdict(list)

        # # prepare to get the loose_fk_objects in bulk from the DB
        # loose_fk_object_paths = [urlparse(url).path for url in resource_urls]
        # loose_fk_objects = get_resources_for_paths(loose_fk_object_paths)
        # # nothing to resolve
        # if loose_fk_objects is None:
        #     loose_fk_object_map = {}
        # else:
        #     # keep the sorting so we can zip them correctly
        #     sorted_objects = sorted(
        #         loose_fk_objects, key=lambda o: o.get_absolute_api_url()
        #     )
        #     loose_fk_object_map = dict(zip(sorted(resource_urls), sorted_objects))

        for authorization in authorizations:
            resource = getattr(authorization, self.loose_fk_field)
            loose_fk_objecten.append(resource)

            # extract the order and map it to the database value
            if authorization.max_vertrouwelijkheidaanduiding:
                choice_item_order = VertrouwelijkheidsAanduiding.get_choice_order(
                    authorization.max_vertrouwelijkheidaanduiding
                )
                va_mapping[choice_item_order].append(resource)

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
                        va_mapping[choice_item_order].append(instance)

        if not use_va:
            return Q(**{f"{prefix}{loose_fk_field}__in": loose_fk_objecten})

        # Combine the filters: group the minimum required confidentiality with
        # the instances (zaaktypen/informatieobjecttypen) for which this constraint
        # applies
        filters = Q()
        for max_va, instances in va_mapping.items():
            filters |= Q(_va_order__lte=max_va) & Q(
                **{f"{prefix}{loose_fk_field}__in": instances}
            )
        return filters

    def get_authorizations(self, scope: Scope, authorizations: models.QuerySet):
        scoped_authorizations = []

        for auth in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(auth.scopes):
                continue

            scoped_authorizations.append(auth)

        return scoped_authorizations

    def get_catalogus_authorizations(
        self, scope: Scope, catalogus_authorizations: models.QuerySet
    ):
        return catalogus_authorizations.filter(scopes__contains=[scope])

    def filter_for_authorizations(
        self,
        scope: Scope,
        authorizations: models.QuerySet,
        catalogus_authorizations: models.QuerySet,
    ) -> models.QuerySet:
        authorizations = self.get_authorizations(scope, authorizations)

        catalogus_authorizations = self.get_catalogus_authorizations(
            scope, catalogus_authorizations
        )

        filters = self.get_filters(
            scope,
            authorizations,
            catalogus_authorizations=catalogus_authorizations,
            use_va=self.vertrouwelijkheidaanduiding_use,
        )
        return self.build_queryset(filters)
