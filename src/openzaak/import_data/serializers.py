from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import HyperlinkedModelSerializer

from openzaak.import_data.models import Import, ImportStatusChoices


class ImportSerializer(HyperlinkedModelSerializer):
    status = SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, instance):
        status = ImportStatusChoices(instance.status)
        return status.label

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
    upload_url = SerializerMethodField()
    status_url = SerializerMethodField()
    report_url = SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_upload_url(self, instance):
        return instance.get_upload_url()

    @extend_schema_field(OpenApiTypes.URI)
    def get_status_url(self, instance):
        return instance.get_status_url()

    @extend_schema_field(OpenApiTypes.URI)
    def get_report_url(self, instance):
        return instance.get_report_url()

    class Meta:
        model = Import
        fields = (
            "upload_url",
            "status_url",
            "report_url",
        )
