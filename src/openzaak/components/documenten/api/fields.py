# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django_loose_fk.drf import FKOrURLField
from rest_framework.fields import empty
from rest_framework.reverse import reverse

from ..models import EnkelvoudigInformatieObjectCanonical


class EnkelvoudigInformatieObjectField(FKOrURLField):
    """
    Custom field to construct the url for models that have a ForeignKey to
    `EnkelvoudigInformatieObject`

    Needed because the canonical `EnkelvoudigInformatieObjectCanonical` no longer stores
    the uuid, but the `EnkelvoudigInformatieObject`s related to it do
    store the uuid
    """

    def to_representation(self, value):
        if not isinstance(value, EnkelvoudigInformatieObjectCanonical):
            return super().to_representation(value)

        value = value.latest_version
        return reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"uuid": value.uuid},
            request=self.context.get("request"),
        )

    def run_validation(self, data=empty):
        value = super().run_validation(data=data)
        if value.pk:
            return value.canonical
        return value
