# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from djangorestframework_camel_case.parser import JSONParser as _JSONParser


class ProblemJSONParser(_JSONParser):
    media_type = "application/problem+json"
