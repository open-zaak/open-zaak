# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from drf_spectacular.generators import (
    EndpointEnumerator as _EndpointEnumerator,
    SchemaGenerator as _SchemaGenerator,
)


class EndpointEnumerator(_EndpointEnumerator):
    """
    include HEAD endpoints
    reused code from vng_api_common.generators.EndpointEnumerator class
    """

    def get_allowed_methods(self, callback) -> list:
        methods = super().get_allowed_methods(callback)

        # head requests are explicitly supported for endpoint that provide caching
        conditional_retrieves = getattr(callback.cls, "_conditional_retrieves", [])
        if not conditional_retrieves:
            return methods

        if set(conditional_retrieves).intersection(callback.actions.values()):
            methods.append("HEAD")

        return methods


class SchemaGenerator(_SchemaGenerator):
    """
    support HEAD method
    """

    endpoint_inspector_cls = EndpointEnumerator

    def create_view(self, callback, method, request=None):
        """
        workaround for HEAD method which doesn't have action
        """
        if method == "HEAD":
            view = super(_SchemaGenerator, self).create_view(
                callback, method, request=request
            )
            return view

        return super().create_view(callback, method, request=request)
