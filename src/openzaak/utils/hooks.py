# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from drf_spectacular.plumbing import (
    get_lib_doc_excludes as default_get_lib_doc_excludes,
)


def preprocess_exclude_endpoints(endpoints, **kwargs):
    """
    preprocessing hook that filters out endpoints from OAS
    """
    exclude = "callbacks"
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if path.split("/")[-1] != exclude
    ]


def get_lib_doc_excludes():
    """
    Exclude ConvertNoneMixin docstring from api spec generation
    """
    from .serializers import ConvertNoneMixin, SubSerializerMixin, ReadOnlyMixin

    return default_get_lib_doc_excludes() + [
        ConvertNoneMixin,
        SubSerializerMixin,
        ReadOnlyMixin,
    ]
