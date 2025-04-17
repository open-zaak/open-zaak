# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from collections import defaultdict
from typing import Dict, Tuple
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Q, When

from django_loose_fk.virtual_models import ProxyMixin
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope
from vng_api_common.utils import get_resources_for_paths

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.utils.query import BlockChangeMixin, LooseFkAuthorizationsFilterMixin

from ..constants import ObjectInformatieObjectTypes
from ..typing import IORelation


class InformatieobjectAuthorizationsFilterMixin(LooseFkAuthorizationsFilterMixin):
    """
    Filter objects whitelisted by the authorizations.

    For DRC, authorizations are defined around ``Autorisatie.informatieobjecttype``,
    with a ``max_vertrouwelijkheidaanduiding`` limiting the confidentiality
    level of ``informatieobjecten`` (inclusive), and scopes that apply for the
    ``informatieobjecttype`` at hand.

    This means that ``informatieobjecten`` are included if, and only if:

    * the ``informatieobjecttype`` is provided in ``authorizations``
    * the scopes for the ``informatieobjecttype`` in each ``authorization`` contain the
      required``scope``
    * the ``informatieobjecttype.vertrouwelijkheidaanduiding`` is less then or equal to the
      ``authorization.max_vertrouwelijkheidaanduiding``

    :param scope: a (possibly complex) scope that must be granted on the
      authorizations
    :param authorizations: queryset of
      :class:`vng_api_common.authorizations.Autorisatie` objects

    :return: a queryset of filtered results according to the
      authorizations provided
    """

    vertrouwelijkheidaanduiding_use = True
    loose_fk_field = "informatieobjecttype"

    @property
    def prefix(self):
        return ""

    def get_filters(
        self,
        scope,
        authorizations,
        catalogus_authorizations=None,
        local=True,
        use_va=True,
    ) -> dict | Q:
        """
        This method was copied over from LooseFkAuthorizationsFilterMixin, because
        changes to optimize the filters made in #1937 seem to break filtering for CMIS.
        Since CMIS is scheduled for removal, we won't spend time to optimize filtering
        for CMIS and preserve the old behavior instead
        """
        if not settings.CMIS_ENABLED:
            return super().get_filters(
                scope,
                authorizations,
                catalogus_authorizations=catalogus_authorizations,
                local=local,
                use_va=use_va,
            )

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
        va_mapping = defaultdict(list)

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
                va_mapping[choice_item_order].append(loose_fk_object)

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

        # Group the When clauses by vertrouwelijkheidaanduiding, to avoid a lot of
        # duplicate `THEN ...` statements
        vertrouwelijkheidaanduiding_whens = [
            When(**{f"{prefix}{loose_fk_field}__in": instances}, then=max_va)
            for max_va, instances in va_mapping.items()
        ]

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

    def build_queryset(self, local_filters, external_filters) -> models.QuerySet:
        order_case = VertrouwelijkheidsAanduiding.get_order_expression(
            "vertrouwelijkheidaanduiding"
        )
        annotations = {"_va_order": order_case}

        if self.authorizations_lookup:
            # If the current queryset is not an InformatieObjectQuerySet, first
            # retrieve the canonical IDs of EnkelvoudigInformatieObjects
            # for which the user is authorized and then return the objects
            # related to those EnkelvoudigInformatieObjectCanonicals
            model = apps.get_model("documenten", "EnkelvoudigInformatieObject")
            if settings.CMIS_ENABLED:
                filtered = model.objects.annotate(**annotations).filter(
                    local_filters | external_filters
                )
            else:
                filtered = (
                    model.objects.annotate(**annotations)
                    .filter(local_filters | external_filters)
                    .values("canonical")
                )
            queryset = self.filter(informatieobject__in=filtered)
            # bring it all together now to build the resulting queryset
        else:
            queryset = self.annotate(**annotations).filter(
                local_filters | external_filters
            )

        return queryset

    def build_queryset_cmis(self, filters) -> models.QuerySet:
        order_case = VertrouwelijkheidsAanduiding.get_order_expression(
            "vertrouwelijkheidaanduiding"
        )
        annotations = {"_va_order": order_case}

        if self.authorizations_lookup:
            # If the current queryset is not an InformatieObjectQuerySet, first
            # retrieve the canonical IDs of EnkelvoudigInformatieObjects
            # for which the user is authorized and then return the objects
            # related to those EnkelvoudigInformatieObjectCanonicals
            model = apps.get_model("documenten", "EnkelvoudigInformatieObject")
            if settings.CMIS_ENABLED:
                filtered = model.objects.annotate(**annotations).filter(**filters)
            else:
                filtered = (
                    model.objects.annotate(**annotations)
                    .filter(filters)
                    .values("canonical")
                )
            queryset = self.filter(informatieobject__in=filtered)
            # bring it all together now to build the resulting queryset
        else:
            queryset = self.annotate(**annotations).filter(**filters)

        return queryset

    def ids_by_auth(
        self, scope, authorizations, catalogus_authorizations=None, local=True
    ) -> models.QuerySet:
        filters = self.get_filters(
            scope,
            authorizations,
            catalogus_authorizations=catalogus_authorizations,
            local=local,
            use_va=self.vertrouwelijkheidaanduiding_use,
        )
        queryset = self.build_queryset_cmis(filters)
        return queryset.values_list("pk", flat=True)

    def filter_for_authorizations(
        self,
        scope: Scope,
        authorizations: models.QuerySet,
        catalogus_authorizations: models.QuerySet,
    ) -> models.QuerySet:
        if not settings.CMIS_ENABLED:
            return super().filter_for_authorizations(
                scope, authorizations, catalogus_authorizations
            )

        # todo implement error if no loose-fk field

        authorizations_local, authorizations_external = self.get_authorizations(
            scope, authorizations
        )

        ids_local = self.ids_by_auth(
            scope,
            authorizations_local,
            catalogus_authorizations=catalogus_authorizations,
            local=True,
        )
        ids_external = self.ids_by_auth(scope, authorizations_external, local=False)
        queryset = self.filter(pk__in=ids_local.union(ids_external))
        return queryset


class InformatieobjectQuerySet(
    InformatieobjectAuthorizationsFilterMixin, models.QuerySet
):
    pass


class InformatieobjectRelatedQuerySet(
    InformatieobjectAuthorizationsFilterMixin, models.QuerySet
):
    authorizations_lookup = "informatieobject"


class ObjectInformatieObjectQuerySet(BlockChangeMixin, InformatieobjectRelatedQuerySet):

    RELATIONS = {
        BesluitInformatieObject: ObjectInformatieObjectTypes.besluit,
        ZaakInformatieObject: ObjectInformatieObjectTypes.zaak,
    }

    def create_from(self, relation: IORelation) -> [models.Model, None]:
        if isinstance(relation.informatieobject, ProxyMixin):
            return None

        # VerzoekInformatieObjecten are not present here, because Open Zaak does not
        # implements Verzoeken API and therefore only supports external `Verzoek`en.
        # Thus this code will never be triggered for `ObjectInformatieObject`en with
        # `object_type=verzoek`
        object_type = self.RELATIONS[type(relation)]
        relation_field = {f"_{object_type}": getattr(relation, object_type)}
        return self.create(
            informatieobject=relation.informatieobject,
            object_type=object_type,
            **relation_field,
        )

    def delete_for(self, relation: IORelation) -> Tuple[int, Dict[str, int]]:
        if isinstance(relation.informatieobject, ProxyMixin):
            return (0, {})

        object_type = self.RELATIONS[type(relation)]
        relation_field = {f"_{object_type}": getattr(relation, object_type)}

        # fetch the instance
        obj = self.get(
            informatieobject=relation.informatieobject,
            object_type=object_type,
            **relation_field,
        )
        return obj.delete()


class DjangoQuerySet(InformatieobjectQuerySet):
    pass


class BestandsDeelQuerySet(models.QuerySet):
    def wipe(self):
        for part in self:
            part.inhoud.delete()
            part.delete()

    @property
    def complete_upload(self) -> bool:
        empty_parts = self.filter(inhoud="")
        return not empty_parts.exists()

    @property
    def empty_bestandsdelen(self) -> bool:
        empty_parts = self.filter(inhoud="")
        return empty_parts.count() == self.count()
