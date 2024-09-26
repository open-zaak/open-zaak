# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_authorizations_have_scopes(data: list[dict]) -> None:
    for entry in data:
        if "scopes" not in entry:
            raise ValidationError(
                _("One or more authorizations are missing scopes."),
                code="missing_scopes",
            )
