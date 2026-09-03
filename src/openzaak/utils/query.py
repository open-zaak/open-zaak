# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import defaultdict
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resource_for_path, get_resources_for_paths


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
    fk_field = None
    vertrouwelijkheidaanduiding_use = True
    authorizations_lookup = None

    @property
    def prefix(self):
        return (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )

    def build_queryset(self, local_filters, external_filters) -> models.QuerySet:
        if self.vertrouwelijkheidaanduiding_use:
            # annotate the queryset so we can map a string value to a logical number
            order_case = VertrouwelijkheidsAanduiding.get_order_expression(
                f"{self.prefix}vertrouwelijkheidaanduiding"
            )
            annotations = {"_va_order": order_case}
            # bring it all together now to build the resulting queryset
            queryset = self.annotate(**annotations).filter(
                local_filters | external_filters
            )

        else:
            queryset = self.filter(local_filters | external_filters)
        return queryset

    def get_filters(
        self,
        scope,
        authorizations,
        catalogus_authorizations=None,
        local=True,
        use_va=True,
    ) -> Q:
        prefix = self.prefix
        fk_field = self.fk_field
        # resource URLs to either use as-is or resolve to database records
        resource_urls = [
            getattr(authorization, self.fk_field) for authorization in authorizations
        ]

        # keep a list of allowed fk objects
        fk_objecten = []
        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        va_mapping = defaultdict(list)

        if not local:
            fk_object_map = dict(zip(resource_urls, resource_urls))
        else:
            # prepare to get the fk_objects in bulk from the DB
            fk_object_paths = [urlparse(url).path for url in resource_urls]
            try:
                fk_objects = get_resources_for_paths(fk_object_paths)
            except RuntimeError:
                # An authorization points to a resource (e.g. a zaaktype) that
                # no longer exists locally. Resolve what we can instead of
                # blowing up the entire request with a 500 - the broken
                # authorization simply grants access to nothing.
                fk_objects = []
                resolvable_urls = []
                for path, url in zip(fk_object_paths, resource_urls):
                    try:
                        fk_objects.append(get_resource_for_path(path))
                        resolvable_urls.append(url)
                    except ObjectDoesNotExist:
                        continue
                resource_urls = resolvable_urls
            # nothing to resolve
            if not fk_objects:
                fk_object_map = {}
            else:
                # keep the sorting so we can zip them correctly
                sorted_objects = sorted(
                    fk_objects, key=lambda o: o.get_absolute_api_url()
                )
                fk_object_map = dict(zip(sorted(resource_urls), sorted_objects))

        for authorization in authorizations:
            resource_url = getattr(authorization, self.fk_field)
            fk_object = fk_object_map.get(resource_url)
            if fk_object is None:
                continue
            fk_objecten.append(fk_object)

            # extract the order and map it to the database value
            if authorization.max_vertrouwelijkheidaanduiding:
                choice_item_order = VertrouwelijkheidsAanduiding.get_choice_order(
                    authorization.max_vertrouwelijkheidaanduiding
                )
                va_mapping[choice_item_order].append(fk_object)

        if catalogus_authorizations:
            for catalogus_authorisation in catalogus_authorizations:
                resources = getattr(
                    catalogus_authorisation.catalogus, f"{self.fk_field}_set"
                ).all()

                for instance in resources:
                    fk_objecten.append(instance)

                    # extract the order and map it to the database value
                    if catalogus_authorisation.max_vertrouwelijkheidaanduiding:
                        choice_item_order = (
                            VertrouwelijkheidsAanduiding.get_choice_order(
                                catalogus_authorisation.max_vertrouwelijkheidaanduiding
                            )
                        )
                        va_mapping[choice_item_order].append(instance)

        if not use_va:
            return Q(**{f"{prefix}{fk_field}__in": fk_objecten})

        # Combine the filters: group the minimum required confidentiality with
        # the instances (zaaktypen/informatieobjecttypen) for which this constraint
        # applies
        filters = Q()
        for max_va, instances in va_mapping.items():
            filters |= Q(_va_order__lte=max_va) & Q(
                **{f"{prefix}{fk_field}__in": instances}
            )
        return filters

    def get_authorizations(self, scope: Scope, authorizations: models.QuerySet):
        authorizations_local = []
        authorizations_external = []

        # There's no external-URL field to fall back on anymore, so every
        # authorization must be resolved against the local database,
        # regardless of the host in the authorization's URL.
        for auth in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(auth.scopes):
                continue

            authorizations_local.append(auth)

        return authorizations_local, authorizations_external

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
        # todo implement error if no loose-fk field

        authorizations_local, authorizations_external = self.get_authorizations(
            scope, authorizations
        )

        catalogus_authorizations = self.get_catalogus_authorizations(
            scope, catalogus_authorizations
        )

        local_filters = self.get_filters(
            scope,
            authorizations_local,
            catalogus_authorizations=catalogus_authorizations,
            local=True,
            use_va=self.vertrouwelijkheidaanduiding_use,
        )
        external_filters = self.get_filters(
            scope,
            authorizations_external,
            local=False,
            use_va=self.vertrouwelijkheidaanduiding_use,
        )
        return self.build_queryset(local_filters, external_filters)
