# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from ..models import ObjectInformatieObject
from ..validators import validate_status


class StatusValidator:
    """
    Wrap around openzaak.components.documenten.models.validate_status to output the errors to the
    correct field.
    """

    def set_context(self, serializer):
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs: dict):
        try:
            validate_status(
                status=attrs.get("status"),
                ontvangstdatum=attrs.get("ontvangstdatum"),
                instance=self.instance,
            )
        except ValidationError as exc:
            raise serializers.ValidationError(exc.error_dict)


class InformatieObjectUniqueValidator:
    """
    Validate that the relation between the object and informatieobject does not
    exist yet in the Documenten component
    """

    message = _("The fields object and infromatieobject must make a unique set.")
    code = "unique"

    def __call__(self, context: OrderedDict):
        informatieobject = context["informatieobject"]
        if settings.CMIS_ENABLED:
            oios = ObjectInformatieObject.objects.filter(**context).exists()
        else:
            oios = informatieobject.objectinformatieobject_set.filter(
                **{context["object_type"]: context["object"]}
            )

        if oios:
            raise serializers.ValidationError(detail=self.message, code=self.code)
