# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from vng_api_common.tests import get_operation_url as _get_operation_url
from vng_api_common.tests.schema import get_spec


def get_operation_url(operation, **kwargs):
    return _get_operation_url(
        operation, spec_path=settings.SPEC_URL["catalogi"], **kwargs
    )


def get_catalogi_spec():
    return get_spec("src/openzaak/components/catalogi/openapi.yaml")
