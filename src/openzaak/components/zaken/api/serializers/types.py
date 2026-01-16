# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from collections import OrderedDict
from typing import Any

from django.db.models.fields.related import RelatedField

from rest_framework.serializers import Serializer

type DRFWritableNestedRelations = OrderedDict[
    str, tuple[RelatedField[Any], Serializer, str]
]
