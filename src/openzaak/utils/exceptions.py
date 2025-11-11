# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from rest_framework import status
from rest_framework.exceptions import APIException
from vng_api_common.schema import HTTP_STATUS_CODE_TITLES


class DetermineProcessEndDateException(Exception):
    pass


class RequestEntityTooLargeException(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_code = "request_entity_too_large"
    default_detail = HTTP_STATUS_CODE_TITLES[status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]
