from django.core.exceptions import ValidationError

from openzaak.components.documenten.models.validators import validate_status
from rest_framework import serializers


class StatusValidator:
    """
    Wrap around openzaak.components.documenten.models.validate_status to output the errors to the
    correct field.
    """

    def set_context(self, serializer):
        self.instance = getattr(serializer, 'instance', None)

    def __call__(self, attrs: dict):
        try:
            validate_status(
                status=attrs.get('status'),
                ontvangstdatum=attrs.get('ontvangstdatum'),
                instance=self.instance
            )
        except ValidationError as exc:
            raise serializers.ValidationError(exc.error_dict)
