import socket
from urllib.parse import urlparse

from django.forms import ModelForm, ValidationError

from .models import NLXConfig


class NLXConfigForm(ModelForm):
    class Meta:
        model = NLXConfig
        fields = ("directory", "outway")

    def clean_outway(self):
        outway = self.cleaned_data["outway"]

        if not outway:
            return outway

        # try to tcp connect to the port
        parsed = urlparse(outway)
        with socket.socket() as s:
            try:
                s.connect((parsed.hostname, parsed.port))
            except ConnectionRefusedError:
                raise ValidationError(
                    "Connection refused. Please, provide a correct address"
                )

        return outway
