# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from functools import cached_property

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from openzaak.utils.serializer_fields import (
    DeprecatedNamespaceLengthHyperlinkedRelatedField,
    FKOrServiceUrlField,
    FKOrServiceUrlValidator,
)

from ..external import (
    ExternalInformatieObjectTypeUnavailable,
    get_external_concept,
)
from ..models import BesluitTypeInformatieObjectType, InformatieObjectType


def is_local(informatieobjecttype) -> bool:
    return getattr(informatieobjecttype, "pk", None) is not None


def get_url(informatieobjecttype) -> str:
    return informatieobjecttype._loose_fk_data["url"]


def is_concept(informatieobjecttype) -> bool:
    if not isinstance(informatieobjecttype, str):
        return bool(informatieobjecttype.concept)

    try:
        return get_external_concept(informatieobjecttype)
    except ExternalInformatieObjectTypeUnavailable as exc:
        raise serializers.ValidationError(
            _(
                "The informatieobjecttype {url} could not be retrieved to check "
                "whether it is a concept."
            ).format(url=informatieobjecttype),
            code="external-informatieobjecttype-unavailable",
        ) from exc


class InformatieObjectTypeUrlField(FKOrServiceUrlField):
    def __init__(self, **kwargs):
        kwargs.setdefault("view_name", "documenten:informatieobjecttype-detail")
        kwargs.setdefault("max_length", 1000)
        super().__init__(**kwargs)

    def run_validation(self, *args, **kwargs):
        self.context.pop(FKOrServiceUrlValidator.get_context_cache_key(self), None)
        return super().run_validation(*args, **kwargs)

    @cached_property
    def _field_instance(self):
        field = DeprecatedNamespaceLengthHyperlinkedRelatedField(
            view_name=self.view_name,
            lookup_field="uuid",
            queryset=InformatieObjectType.objects.all(),
        )
        field.parent = self.parent
        return field


class BesluitTypeInformatieObjectTypeUrlField(InformatieObjectTypeUrlField):
    def _get_model_and_field(self) -> tuple:
        return (
            BesluitTypeInformatieObjectType,
            BesluitTypeInformatieObjectType._meta.get_field("informatieobjecttype"),
        )


class BesluitTypeInformatieObjectTypenField(serializers.ListField):
    def __init__(self, **kwargs):
        kwargs.setdefault("child", BesluitTypeInformatieObjectTypeUrlField())
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return [
            relation._iotype_url or relation._informatieobjecttype
            for relation in instance.besluittypeinformatieobjecttype_set.all()
        ]
