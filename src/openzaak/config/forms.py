# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging
import socket
from typing import Dict
from urllib.parse import urlparse

from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as _

import requests
from zgw_consumers.models import Service

from openzaak.nlx.api import get_services

from .models import InternalService, NLXConfig

logger = logging.getLogger(__name__)


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


def get_nlx_choices() -> Dict[str, dict]:
    choices = {}
    nlx_outway = NLXConfig.get_solo().outway
    try:
        services = get_services()
    except requests.RequestException:
        logger.warning("Failed fetching the NLX services", exc_info=True)
        return {}

    for service in services:
        url = f"{nlx_outway}{service['organization_name']}/{service['service_name']}/"
        service_data = {
            "service_name": service["service_name"],
            "oas": service.get("documentation_url", ""),
        }
        choices.setdefault(service["organization_name"], {}).update({url: service_data})

    return choices


class ExternalServiceForm(ModelForm):
    class Meta:
        model = Service
        fields = (
            "api_root",
            "api_type",
            "label",
            "auth_type",
            "nlx",
            "client_id",
            "secret",
            "user_id",
            "user_representation",
            "header_key",
            "header_value",
            "oas",
        )
