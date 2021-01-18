# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Dict, Tuple

from django.apps import apps
from django.conf import settings
from django.db import models

from django_loose_fk.virtual_models import ProxyMixin
from vng_api_common.constants import ObjectTypes, VertrouwelijkheidsAanduiding

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.utils.query import BlockChangeMixin, LooseFkAuthorizationsFilterMixin

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

    def build_queryset(self, filters) -> models.QuerySet:
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
                    .filter(**filters)
                    .values("canonical")
                )
            queryset = self.filter(informatieobject__in=filtered)
            # bring it all together now to build the resulting queryset
        else:
            queryset = self.annotate(**annotations).filter(**filters)

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
        BesluitInformatieObject: ObjectTypes.besluit,
        ZaakInformatieObject: ObjectTypes.zaak,
    }

    def create_from(self, relation: IORelation) -> [models.Model, None]:
        if isinstance(relation.informatieobject, ProxyMixin):
            return None

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
