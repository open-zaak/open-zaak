# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from dataclasses import dataclass
from typing import List

from django.contrib.sites.models import Site
from django.urls import reverse

import requests

from openzaak.utils import build_absolute_url

from .datastructures import Output
from .exceptions import SelfTestFailure


@dataclass
class SiteConfiguration:
    """
    Configure the application site/domain.

    From: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config.html#setting-the-domain

    FIXME: perhaps set up pub-sub with redis to flush the process site cache? See
    open-zaak/open-zaak#598
    """

    domain: str
    organization_name: str

    def configure(self) -> List[Output]:
        site = Site.objects.get_current()
        # no-op - we only check based on domain
        if site.domain == self.domain:
            return []

        # TODO: configure and include settings.ENVIRONMENT (currently hardcoded in settings files)
        site.domain = self.domain
        site.name = f"Open Zaak {self.organization_name}".strip()
        site.save()
        return []

    def test_configuration(self) -> List[Output]:
        full_url = build_absolute_url(reverse("home"), request=None)
        try:
            response = requests.get(full_url)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailure(
                f"Could not access home page at '{full_url}'"
            ) from exc

        return [
            Output(
                id="domainCheck",
                title="Domain test succeeded",
                data={"response_status": response.status_code},
            )
        ]
