from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class LengthHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    """
    replace build-in 'no_match' error code with `bad-url` to make it consistent with
    reference implementation
    """
    default_error_messages = {
        "max_length": _("Ensure this field has no more than {max_length} characters."),
        "min_length": _("Ensure this field has at least {min_length} characters."),
        "bad-url": "Please provide a valid URL."
    }

    def __init__(self, **kwargs):
        self.max_length = kwargs.pop("max_length", None)
        self.min_length = kwargs.pop("min_length", None)

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if self.max_length and len(data) > self.max_length:
            self.fail("max_length", max_length=self.max_length, length=len(data))

        if self.min_length and len(data) < self.min_length:
            self.fail("min_length", max_length=self.min_length, length=len(data))

        return super().to_internal_value(data)

    def fail(self, key, **kwargs):
        if key == 'no_match':
            key = 'bad-url'
        super().fail(key, **kwargs)
