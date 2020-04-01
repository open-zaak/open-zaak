import socket
from urllib.parse import urlparse

from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.models import Service

from .models import InternalService, NLXConfig


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
            s.settimeout(2)  # 2 seconds
            try:
                s.connect((parsed.hostname, parsed.port))
            except ConnectionRefusedError:
                raise ValidationError(
                    _("Connection refused. Please, provide a correct address")
                )

        return outway


class InternalServiceForm(ModelForm):
    class Meta:
        model = InternalService
        fields = ("enabled", "nlx")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)

        if instance and instance.component == "autorisaties":
            self.fields["enabled"].disabled = True


class ExternalServiceForm(ModelForm):
    class Meta:
        model = Service
        fields = ("api_root", "api_type", "label", "auth_type", "nlx")
