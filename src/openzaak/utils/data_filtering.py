# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
class ListFilterByAuthorizationsMixin:
    """
    Filter list-action data by the authorizations configured.

    Authorizations configured for a client/consumer have a run-time effect
    in _which_ data is effectively exposed. This ``get_queryset``
    implementation facilitates it in a conventional way.

    For this to be effective, the underlying model must have a queryset
    method ``filter_for_authorizations``, which is provided by
    :class:`zrc.datamodel.query.AuthorizationsFilterMixin`
    """

    def get_queryset(self):
        base = super().get_queryset()

        # drf-yasg introspection - doesn't run the middleware, so this isn't set
        if not hasattr(self.request, "jwt_auth"):
            return base

        # we do not apply the filtering for update/partial_update/delete,
        # because the resource _does exist_, you just don't have permission
        # to do those operations. A 403 is semantically more correct than a
        # 404, which would be the result if the queryset is always filtered.
        if not self.action == "list":
            return base

        # get the auth apps that are relevant for this particular request
        apps = self.request.jwt_auth.applicaties

        # as soon as there's one matching app that gives you all permissions,
        # you're good - no further detailed data filtering is applied
        if any(app.heeft_alle_autorisaties for app in apps):
            return base

        scope_needed = self.required_scopes[self.action]
        component = base.model._meta.app_label
        authorizations = self.request.jwt_auth.get_autorisaties(component)

        return base.filter_for_authorizations(scope_needed, authorizations)
