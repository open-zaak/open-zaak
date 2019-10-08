from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class PublishValidator:
    code = "not-published"
    message = _("The resource is not published.")

    def __call__(self, value):
        if value.concept:
            raise serializers.ValidationError(self.message, code=self.code)
