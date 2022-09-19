# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from pathlib import Path

from django.conf import settings

from vng_api_common.tests.schema import get_spec as _read_spec


def get_spec(component: str) -> dict:
    full_path = (
        Path(settings.DJANGO_PROJECT_DIR) / "components" / component / "openapi.yaml"
    )
    return _read_spec(str(full_path))
