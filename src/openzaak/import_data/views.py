# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import csv
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from django_sendfile import sendfile
from rest_framework import status, viewsets
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.generics import mixins
from rest_framework.parsers import BaseParser
from rest_framework.response import Response

from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.permissions import ImportAuthRequired
from openzaak.import_data.serializers import ImportCreateSerializer, ImportSerializer


class ImportMixin:
    def validate_existing_imports(self, instance=None):
        existing_imports = self.get_queryset()

        active_imports = existing_imports.filter(
            import_type=self.import_type, status__in=ImportStatusChoices.started_choices
        )

        if instance:
            active_imports = active_imports.exclude(pk=instance.pk)

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


class ImportCreateview(ImportMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    import_type: ImportTypeChoices

    serializer_class = ImportCreateSerializer

    permission_classes = (ImportAuthRequired,)

    def get_queryset(self):
        return Import.objects.all()

    def create(self, request, *args, **kwargs):
        self.validate_existing_imports()

        import_instance = Import.objects.create(
            status=ImportStatusChoices.pending,
            import_type=self.import_type,
            # This should be updated when the import metadata file is parsed
            total=0,
        )

        serializer = self.get_serializer_class()(instance=import_instance)

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED,
            content_type="application/json",
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
    csv_reader = csv.reader(import_data, delimiter=",", quotechar='"')

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


class ImportUploadView(ImportMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    lookup_field: str = "uuid"
    parser_classes = (CSVParser,)
    permission_classes = (ImportAuthRequired,)

    import_type: ImportTypeChoices
    import_headers: list[str]

    @property
    def import_dir(self) -> Path:
        raise NotImplementedError

    def get_queryset(self):
        return Import.objects.filter(import_type=self.import_type)

    def get_import_headers(self) -> list[str]:
        return self.import_headers

    def create(self, request, *args, **kwargs):
        import_instance = self.get_object()

        self.validate_existing_imports(instance=import_instance)

        import_dir = self.import_dir

        if not import_dir.exists():
            error_message = _(
                "The import was not started as the import directory %s could not "
                "be found"
            ) % str(import_dir)
            code = "import-dir-not-found"
            raise ValidationError({"__all__": [error_message]}, code=code)
        elif not import_dir.is_dir():
            error_message = _(
                "The import was not started as the specified import  "
                "directory is not a directory: %s"
            ) % str(import_dir)
            code = "import-dir-not-dir"
            raise ValidationError({"__all__": [error_message]}, code=code)

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

        if not request_data:
            error_message = _(
                "The import process cannot be started with an empty import file."
            )
            raise ValidationError({"__all__": [error_message]}, code="empty-file")

        validate_headers(StringIO(request_data, newline=""), self.get_import_headers())

        import_instance.import_file = ContentFile(
            request.data, name=f"{import_instance.uuid}-import.csv"
        )
        import_instance.status = ImportStatusChoices.active
        import_instance.save(update_fields=["status", "import_file"])

        return Response(status=status.HTTP_200_OK)


class ImportStatusView(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    import_type: ImportTypeChoices
    serializer_class = ImportSerializer
    permission_classes = (ImportAuthRequired,)

    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(
            import_type=self.import_type, status__in=ImportStatusChoices.visible_choices
        )


class ImportReportView(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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
            request,
            instance.report_file.path,
            attachment=True,
            mimetype="text/csv",
        )


class ImportDestroyView(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    import_type: ImportTypeChoices
    permission_classes = (ImportAuthRequired,)
    lookup_field = "uuid"

    def get_queryset(self):
        return Import.objects.filter(import_type=self.import_type)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status not in ImportStatusChoices.deletion_choices:
            message = (
                _("Import cannot be deleted due to current status: %s")
                % instance.status
            )

            raise ValidationError({"__all__": message}, code="import-invalid-status")

        return super().destroy(request, *args, **kwargs)
