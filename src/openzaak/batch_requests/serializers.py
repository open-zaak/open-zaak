from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

VALID_METHODS = [
    ("get", "GET"),
]


class RequestSerializer(serializers.Serializer):
    method = serializers.ChoiceField(label=_("HTTP method"), choices=VALID_METHODS,)
    url = serializers.CharField(label=_("URL or absolute path to call"))

    def validate_url(self, value: str):
        # TODO: validate that the URL resolves
        return value
