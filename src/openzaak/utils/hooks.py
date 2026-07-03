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
    from .serializers import ConvertNoneMixin, ReadOnlyMixin, SubSerializerMixin

    return default_get_lib_doc_excludes() + [
        ConvertNoneMixin,
        SubSerializerMixin,
        ReadOnlyMixin,
    ]


DEPRECATED_URLCONFS = ["openzaak.components.besluiten.api.urls"]


def postprocess_deprecate_apis(result, generator, request, public):
    """
    Deprecates all methods of for the url configs in DEPRECATED_URLCONFS.
    """
    if generator.urlconf in DEPRECATED_URLCONFS:
        for path in result["paths"]:
            for method in result["paths"][path]:
                result["paths"][path][method]["deprecated"] = True
    return result
