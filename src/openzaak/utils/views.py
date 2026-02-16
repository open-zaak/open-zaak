# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import structlog
from rest_framework import exceptions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from vng_api_common.audittrails.viewsets import (
    AuditTrailViewSet as _AuditTrailViewSet,
)
from vng_api_common.views import (
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


def azure_error_handler(exc, context):
    error_message = "Error occurred while connecting with Azure"
    exc.detail = error_message
    exc.default_detail = error_message
    exc.status_code = status.HTTP_502_BAD_GATEWAY

    return Response(
        {"detail": error_message},
        status=status.HTTP_502_BAD_GATEWAY,
    )
