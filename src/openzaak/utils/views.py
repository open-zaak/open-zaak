# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import csv
from io import StringIO

from django import http
from django.apps import apps
from django.conf import settings
from django.template import TemplateDoesNotExist, loader
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME

import requests
from django_sendfile import sendfile
from rest_framework import exceptions, status, viewsets
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView
from vng_api_common.audittrails.viewsets import AuditTrailViewSet as _AuditTrailViewSet
from vng_api_common.views import ViewConfigView as _ViewConfigView, _test_sites_config
from zds_client import ClientError

from openzaak.utils.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.utils.permissions import ImportAuthRequired
from openzaak.utils.serializers import ImportSerializer
from openzaak.utils.tasks import import_documents


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


class ImportCreateview(CreateAPIView):
    import_type: ImportTypeChoices

    permission_classes = (ImportAuthRequired,)

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


class CSVParser(BaseParser):
    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)

        try:
            raw_data = stream.read()
            data = raw_data.decode(encoding)
            csv_reader = csv.reader(data)
            len([row for row in csv_reader])
        except (ValueError, csv.Error) as e:
            raise ParseError(_("Unable to parse CSV file: %s") % force_str(e))

        return data


def validate_headers(import_data: StringIO, expected_headers: list[str]) -> None:
    csv_reader = csv.reader(import_data, delimiter=",")

    headers = next(csv_reader, [])
    missing_headers = [
        expected_header
        for expected_header in expected_headers
        if expected_header not in headers
    ]

    if missing_headers:
        error_message = _(
            "The following headers were not found in the CSV file: %s"
        ) % ",".join(missing_headers)

        raise ValidationError(
            {"__all__": [error_message]}, code="missing-import-headers"
        )


class ImportUploadView(GenericAPIView):
    lookup_field: str = "uuid"
    parser_classes = (CSVParser,)
    permission_classes = (ImportAuthRequired,)

    import_type: ImportTypeChoices
    import_headers: list[str] = []

    def get_queryset(self):
        return Import.objects.filter(import_type=self.import_type)

    def get_import_headers(self) -> list[str]:
        return self.import_headers

    def post(self, request, *args, **kwargs):
        import_instance = self.get_object()

        if import_instance.status != ImportStatusChoices.pending:
            import_status = ImportStatusChoices(import_instance.status)
            error_message = (
                _(
                    "Starting an import process is not possible due to the current "
                    "status of the import: %s"
                )
                % import_status.label
            )
            raise ValidationError({"__all__": [error_message]}, code="invalid-status")

        request_data = request.data or ""

        validate_headers(StringIO(request_data), self.get_import_headers())

        import_instance.status = ImportStatusChoices.active
        import_instance.save(update_fields=["status"])

        import_documents.delay(import_instance.pk)

        return Response(status=status.HTTP_200_OK)


class ImportStatusView(RetrieveAPIView):
    import_type: ImportTypeChoices
    serializer_class = ImportSerializer
    permission_classes = (ImportAuthRequired,)

    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(
            import_type=self.import_type, status__in=ImportStatusChoices.visible_choices
        )


class ImportReportView(RetrieveAPIView):
    import_type: ImportTypeChoices
    permission_classes = (ImportAuthRequired,)
    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(
            import_type=self.import_type,
            status__in=ImportStatusChoices.report_choices,
            report_file__isnull=False,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        return sendfile(
            request, instance.report_file.path, attachment=True, mimetype="text/csv",
        )
