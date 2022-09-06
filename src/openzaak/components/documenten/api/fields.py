# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.core.validators import URLValidator

from django_loose_fk.drf import FKOrURLField
from rest_framework.fields import empty
from rest_framework.reverse import reverse

from openzaak.utils.serializer_fields import FKOrServiceUrlField

from ..constants import ObjectInformatieObjectTypes
from ..models import EnkelvoudigInformatieObjectCanonical, ObjectInformatieObject


class EnkelvoudigInformatieObjectField(FKOrServiceUrlField):
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


class OnlyRemoteOrFKOrURLField(FKOrURLField):
    only_remote_object_types = (ObjectInformatieObjectTypes.verzoek,)

    def get_attribute(self, instance: ObjectInformatieObject):
        if self.source in self.only_remote_object_types:
            # deliberately pick the base class of the FKOrURLField to get the attribute
            return super(FKOrURLField, self).get_attribute(instance)
        return super().get_attribute(instance)

    def run_validation(self, data):
        if self.source in self.only_remote_object_types:
            validate_url = URLValidator()
            validate_url(data)
            return super(FKOrURLField, self).run_validation(data)
        return super().run_validation(data)
