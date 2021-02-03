# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from djangorestframework_camel_case.render import JSONRenderer as _JSONRenderer


class ProblemJSONRenderer(_JSONRenderer):
    media_type = "application/problem+json"
