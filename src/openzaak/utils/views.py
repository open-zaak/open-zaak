# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import http
from django.template import TemplateDoesNotExist, loader
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME

from rest_framework import exceptions, viewsets
from rest_framework.views import APIView
from vng_api_common.audittrails.viewsets import AuditTrailViewSet as _AuditTrailViewSet
from vng_api_common.views import (
    ViewConfigView as _ViewConfigView,
    _test_nrc_config,
    _test_sites_config,
)


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_500_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseServerError(
            "<h1>Server Error (500)</h1>", content_type="text/html"
        )
    context = {"request": request}
    return http.HttpResponseServerError(template.render(context))


class ViewConfigView(_ViewConfigView):
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
