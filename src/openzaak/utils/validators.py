from django.utils.translation import ugettext_lazy as _

from django_loose_fk.drf import FKOrURLField, FKOrURLValidator
from rest_framework import serializers
from vng_api_common.validators import IsImmutableValidator


class PublishValidator(FKOrURLValidator):
    publish_code = "not-published"
    publish_message = _("The resource is not published.")

    def set_context(self, serializer_field):
        # loose-fk field
        if isinstance(serializer_field, FKOrURLField):
            super().set_context(serializer_field)

    def __call__(self, value):
        # loose-fk field
        if value and isinstance(value, str):
            super().__call__(value)
            value = self.resolver.resolve(self.host, value)

        if value.concept:
            raise serializers.ValidationError(
                self.publish_message, code=self.publish_code
            )


class LooseFkIsImmutableValidator(FKOrURLValidator):
    """
    Valideer dat de waarde van het FkOrUrlField niet wijzigt bij een update actie.
    """

    def __init__(self, *args, **kwargs):
        self.instance_path = kwargs.pop("instance_path", None)
        super().__init__(*args, **kwargs)

    def set_context(self, serializer_field):
        # loose-fk field
        if isinstance(serializer_field, FKOrURLField):
            super().set_context(serializer_field)

        # Determine the existing instance, if this is an update operation.
        self.serializer_field = serializer_field
        self.instance = getattr(serializer_field.parent, "instance", None)

    def __call__(self, new_value):
        # no instance -> it's not an update
        if not self.instance:
            return

        current_value = getattr(self.instance, self.serializer_field.field_name)

        # loose-fk field
        if new_value and isinstance(new_value, str):
            super().__call__(new_value)
            new_value = self.resolver.resolve(self.host, new_value)

        if self.instance_path:
            for bit in self.instance_path.split("."):
                new_value = getattr(new_value, bit)

        if new_value != current_value:
            raise serializers.ValidationError(
                IsImmutableValidator.message, code=IsImmutableValidator.code
            )
