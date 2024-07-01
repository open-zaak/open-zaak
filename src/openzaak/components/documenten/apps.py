# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from vng_api_common.serializers import GegevensGroepSerializer
from vng_api_common.utils import underscore_to_camel


class DocumentenConfig(AppConfig):
    name = "openzaak.components.documenten"
    verbose_name = _("Documenten")

    def ready(self):
        # load the signal receivers
        from . import signals  # noqa

        # Initialize the viewset for Kanaal.get_usage
        from .api.viewsets import EnkelvoudigInformatieObjectViewSet  # noqa

        validate_eio_headers()


def validate_eio_headers() -> None:
    """
    Validates that no serializer fields are missing in the `DocumentRow` class
    """
    if settings.CMIS_ENABLED:
        return

    from .api.serializers import EnkelvoudigInformatieObjectSerializer
    from .import_utils import DocumentRow

    excluded_fields = (
        "locked",
        "inhoud",
        "bestandsdelen",
        "begin_registratie",
        "versie",
        "url",
    )

    serializer = EnkelvoudigInformatieObjectSerializer()
    fields = serializer.fields.items()
    nested_fields = {
        field_name: list(field.fields.keys())
        for field_name, field in fields
        if isinstance(field, GegevensGroepSerializer)
    }
    csv_nested_fields = {
        f"{field_parent}.{field_child}"
        for field_parent, children in nested_fields.items()
        for field_child in children
    }

    expected_fields = {
        underscore_to_camel(field)
        for field in EnkelvoudigInformatieObjectSerializer.Meta.fields
        if field not in (*excluded_fields, *nested_fields.keys())
    }

    expected_fields.update(csv_nested_fields)

    document_row_fields = {
        field for field in DocumentRow.import_headers if field in expected_fields
    }

    missing_fields = expected_fields - document_row_fields

    if missing_fields:
        raise ImproperlyConfigured(
            "The following fields are missing from the `DocumentRow` class: "
            f"{','.join(missing_fields)}"
        )
