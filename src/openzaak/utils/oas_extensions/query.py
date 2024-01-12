# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from drf_spectacular.contrib.django_filters import DjangoFilterExtension
from vng_api_common.utils import underscore_to_camel


class CamelizeFilterExtension(DjangoFilterExtension):
    priority = 1

    def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
        """
        camelize query parameters
        """
        parameters = super().get_schema_operation_parameters(
            auto_schema, *args, **kwargs
        )

        for parameter in parameters:
            parameter["name"] = underscore_to_camel(parameter["name"])

        return parameters
