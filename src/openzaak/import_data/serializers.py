# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.utils.translation import gettext as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import HyperlinkedModelSerializer

from openzaak.import_data.models import Import, ImportStatusChoices


class ImportSerializer(HyperlinkedModelSerializer):
    status = SerializerMethodField(source="get_status")

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, instance):
        status = ImportStatusChoices(instance.status)
        return status.value

    class Meta:
        model = Import
        fields = (
            "total",
            "processed",
            "processed_successfully",
            "processed_invalid",
            "status",
        )


class ImportCreateSerializer(HyperlinkedModelSerializer):
    upload_url = SerializerMethodField(
        help_text=_(
            "De URL waar het metadata bestand geupload kan worden. Dit start "
            "vervolgens de IMPORT."
        )
    )
    status_url = SerializerMethodField(
        help_text=_("De URL waar de status van de IMPORT opgevraagd kan worden.")
    )
    report_url = SerializerMethodField(
        help_text=_(
            "De URL waar het rapportage bestand gedownload kan worden van de IMPORT "
            "wanneer deze is afgerond."
        )
    )

    @extend_schema_field(OpenApiTypes.URI)
    def get_upload_url(self, instance):
        return instance.get_upload_url(request=self.context.get("request"))

    @extend_schema_field(OpenApiTypes.URI)
    def get_status_url(self, instance):
        return instance.get_status_url(request=self.context.get("request"))

    @extend_schema_field(OpenApiTypes.URI)
    def get_report_url(self, instance):
        return instance.get_report_url(request=self.context.get("request"))

    class Meta:
        model = Import
        fields = (
            "upload_url",
            "status_url",
            "report_url",
        )
