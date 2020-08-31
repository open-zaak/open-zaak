# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import OrderedDict

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
        # The context contains the keys: informatieobject (eio), object_type (whether it is a relation with zaak or
        # besluit) and 'object' (the actual zaak or besluit). The 'object' key needs to be replaced with 'zaak'
        # or 'besluit' as there is no 'object' attribute in the objectinformatieobject model.
        zaak_or_besluit_object = context.pop("object")
        context.update({context["object_type"]: zaak_or_besluit_object})

        oios = ObjectInformatieObject.objects.filter(**context).exists()

        if oios:
            raise serializers.ValidationError(detail=self.message, code=self.code)
