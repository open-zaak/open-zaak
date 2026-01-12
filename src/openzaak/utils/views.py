# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

import os
from collections import OrderedDict

import sentry_sdk
import structlog
from azure.core.exceptions import AzureError
from rest_framework import exceptions, exceptions as drf_exceptions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler as drf_exception_handler
from vng_api_common.audittrails.viewsets import AuditTrailViewSet as _AuditTrailViewSet
from vng_api_common.exception_handling import HandledException
from vng_api_common.views import (
    ERROR_CONTENT_TYPE,
    ViewConfigView as _ViewConfigView,
    _test_nrc_config,
    _test_sites_config,
)

logger = structlog.stdlib.get_logger(__name__)


class ViewConfigView(_ViewConfigView):
    template_name = "view_config.html"

    def get_context_data(self, **kwargs):
        context = {}

        config = []
        config += _test_sites_config(self.request)
        # Do not check autorisaties channel subscription, because Open Zaak is the provider
        # of the Autorisaties API
        config += _test_nrc_config(check_autorisaties_subscription=False)

        context["config"] = config
        return context


class ErrorDocumentView(APIView):
    exception_cls = exceptions.APIException
    schema = None  # do not document this in the API specs

    def get(self, request):
        raise self.exception_cls()


class AuditTrailViewSet(_AuditTrailViewSet):
    def initialize_request(self, request, *args, **kwargs):
        # workaround for drf-nested-viewset injecting the URL kwarg into request.data
        return super(viewsets.GenericViewSet, self).initialize_request(
            request, *args, **kwargs
        )


# TODO allow defining an error-response mapping and bring this back to the lib
def exception_handler(exc, context):
    """
    Transform 4xx and 5xx errors into DSO-compliant shape.
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        if os.getenv("DEBUG", "").lower() in ["yes", "1", "true"]:
            return None

        logger.exception("api.uncaught_exception", message=str(exc), exc_info=True)

        # make sure the exception still ends up in Sentry
        sentry_sdk.capture_exception(exc)

        if isinstance(exc, AzureError):
            exc = drf_exceptions.APIException(
                "Error occurred while connecting with Azure"
            )
            response = Response(status=status.HTTP_502_BAD_GATEWAY)
        else:
            # unknown type, so we use the generic Internal Server Error
            exc = drf_exceptions.APIException("Internal Server Error")
            response = Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    request = context.get("request")

    serializer = HandledException.as_serializer(exc, response, request)
    response.data = OrderedDict(serializer.data.items())
    # custom content type
    response["Content-Type"] = ERROR_CONTENT_TYPE
    return response
