# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import List

import requests

from openzaak.config.models import NLXConfig


def get_services() -> List[dict]:
    directory = NLXConfig.get_solo().directory_url
    url = f"{directory}api/directory/list-services"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()["services"]
