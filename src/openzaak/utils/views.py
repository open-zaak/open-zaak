# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import http
from django.apps import apps
from django.template import TemplateDoesNotExist, loader
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME

import requests
from rest_framework import exceptions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from vng_api_common.audittrails.viewsets import AuditTrailViewSet as _AuditTrailViewSet
from vng_api_common.views import ViewConfigView as _ViewConfigView, _test_sites_config
from zds_client import ClientError

from openzaak.utils.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.utils.serializers import ImportSerializer


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
        config += _test_nrc_config()

        context["config"] = config
        return context


def _test_nrc_config() -> list:
    if not apps.is_installed("notifications_api_common"):
        return []

    from notifications_api_common.models import NotificationsConfig

    nrc_config = NotificationsConfig.get_solo()

    nrc_client = NotificationsConfig.get_client()

    has_nrc_auth = nrc_client.auth is not None

    if not nrc_config.notifications_api_service:
        checks = [((_("NRC"), _("Missing"), False))]
        return checks

    checks = [
        (
            _("NRC"),
            nrc_config.notifications_api_service.api_root,
            nrc_config.notifications_api_service.api_root.endswith("/"),
        ),
        (
            _("Credentials for NRC"),
            _("Configured") if has_nrc_auth else _("Missing"),
            has_nrc_auth,
        ),
    ]

    # check if permissions in AC are fine
    if has_nrc_auth:
        error = False

        try:
            nrc_client.list("kanaal")
        except requests.ConnectionError:
            error = True
            message = _("Could not connect with NRC")
        except ClientError as exc:
            error = True
            message = _(
                "Cannot retrieve kanalen: HTTP {status_code} - {error_code}"
            ).format(status_code=exc.args[0]["status"], error_code=exc.args[0]["code"])
        else:
            message = _("Can retrieve kanalen")

        checks.append((_("NRC connection and authorizations"), message, not error))

    return checks


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


# TODO: add permissions
class ImportCreateview(CreateAPIView):
    import_type: ImportTypeChoices

    def get_queryset(self):
        return Import.objects.all()

    def create(self, request, *args, **kwargs):
        existing_imports = self.get_queryset()
        active_imports = existing_imports.filter(
            import_type=self.import_type, status__in=ImportStatusChoices.started_choices
        )

        if active_imports:
            raise ValidationError(
                {
                    "__all__": [
                        _(
                            "Er is een import process gaande. Probeer het later"
                            " nogmaals."
                        )
                    ]
                },
                code="existing-import-started",
            )

        import_instance = Import.objects.create(
            status=ImportStatusChoices.pending,
            import_type=self.import_type,
            # This should be updated when the import metadata file is parsed
            total=0,
        )

        return Response(
            data={
                "upload_url": import_instance.get_upload_url(request=request),
                "status_url": import_instance.get_status_url(request=request),
                "report_url": import_instance.get_report_url(request=request),
            },
            status=status.HTTP_201_CREATED,
        )


# TODO: add permissions
class ImportUploadView(CreateAPIView):
    import_type: ImportTypeChoices
    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.all()

    # TODO: start celery task which will kickstart the import proces
    def create(self, request, *args, **kwargs):
        raise NotImplementedError


# TODO: add permissions
class ImportStatusView(RetrieveAPIView):
    import_type: ImportTypeChoices
    serializer_class = ImportSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(
            import_type=self.import_type, status__in=ImportStatusChoices.visible_choices
        )


# TODO: add permissions
class ImportReportView(RetrieveAPIView):
    import_type: ImportTypeChoices
    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(
            import_type=self.import_type,
            status__in=ImportStatusChoices.report_choices,
            report_file__isnull=False,
        )

    # TODO: return csv report
    def retrieve(self, request, *args, **kwargs):
        raise NotImplementedError
