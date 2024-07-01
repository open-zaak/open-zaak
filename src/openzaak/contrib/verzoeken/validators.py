# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.conf import settings

from openzaak.utils.auth import get_auth
from openzaak.utils.validators import ResourceValidator

verzoek_validator = ResourceValidator(
    "Verzoek",
    settings.VRC_API_STANDARD,
    get_auth=get_auth,
)
