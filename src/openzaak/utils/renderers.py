# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import orjson
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from rest_framework.renderers import JSONRenderer
from vng_api_common.views import ERROR_CONTENT_TYPE


class ProblemJSONRenderer(CamelCaseJSONRenderer):
    media_type = ERROR_CONTENT_TYPE


class ORJSONRenderer(JSONRenderer):
    """
    Custom JSON renderer using `orjson` for faster JSON serialization.
    It also ensures that the output is in camel case.
    """

    json_underscoreize = api_settings.JSON_UNDERSCOREIZE

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Convert the data to camel case
        data = camelize(data, **self.json_underscoreize)
        # Use orjson to serialize the data
        json_data = orjson.dumps(data)
        return json_data
