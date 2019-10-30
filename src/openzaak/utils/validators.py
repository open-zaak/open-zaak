from django.utils.translation import ugettext_lazy as _

from django_loose_fk.drf import FKOrURLField, FKOrURLValidator
from rest_framework import serializers


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
