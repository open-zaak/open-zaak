# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from pathlib import Path

from open_api_framework.conf.utils import get_django_project_dir
from vng_api_common.tests.schema import get_spec as _read_spec


def get_spec(component: str) -> dict:
    project_dir = get_django_project_dir()
    full_path = Path(project_dir) / "components" / component / "openapi.yaml"
    return _read_spec(str(full_path))
